import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import database
import models
from main import app
from routes import auth_routes, orders_routes


class CheckoutFlowTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        database.engine = self.engine
        database.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        models.Base.metadata.create_all(bind=self.engine)

        self.db = database.SessionLocal()
        self.category = models.Category(name="Kinh tế", slug="kinh-te", icon="📖")
        self.db.add(self.category)
        self.db.commit()
        self.db.refresh(self.category)

        self.user = models.User(
            username="buyer_checkout",
            email="buyer_checkout@example.com",
            hashed_password="hashedpw",
            full_name="Buyer Checkout",
            role=models.UserRole.BUYER.value,
            status=models.UserStatus.ACTIVE.value,
            phone="0909000000",
            address="HCM",
        )
        self.db.add(self.user)
        self.db.commit()
        self.db.refresh(self.user)

        self.book = models.Book(
            seller_id=self.user.id,
            category_id=self.category.id,
            title="Sách Mua Nhanh",
            author="Tác giả Mua Nhanh",
            publisher="NXB Test",
            price=120000,
            discount_price=100000,
            stock=10,
            cover_image="https://example.com/cover.jpg",
            description="Mô tả sách",
            status=models.BookStatus.APPROVED.value,
            sold_count=0,
            rating=4.8,
        )
        self.db.add(self.book)
        self.db.commit()
        self.db.refresh(self.book)

        self.voucher = models.Voucher(
            code="TEST20",
            name="Giảm 20.000đ",
            discount_type="FIXED",
            discount_value=20000,
            min_order_amount=50000,
            usage_limit=5,
        )
        self.db.add(self.voucher)
        self.db.commit()

        def override_get_db():
            db = database.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[database.get_db] = override_get_db
        app.dependency_overrides[auth_routes.get_db] = override_get_db
        app.dependency_overrides[orders_routes.get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.db.close()

    def test_guest_cannot_create_buy_now_checkout(self):
        response = self.client.post(
            "/api/orders/checkout/instant",
            json={
                "book_id": self.book.id,
                "quantity": 1,
                "shipping_name": "Buyer",
                "shipping_phone": "0900000000",
                "shipping_address": "123 ABC",
                "payment_method": "COD",
            },
        )
        self.assertEqual(response.status_code, 401)

    def test_logged_in_user_can_get_checkout_session(self):
        login = self.client.post(
            "/api/auth/login",
            json={"username": self.user.username, "password": "123456"},
        )
        self.assertEqual(login.status_code, 401)

        token = "dummy-token"
        # Directly create JWT to bypass password complexity for this test
        import auth as auth_module

        token = auth_module.create_access_token({"sub": self.user.username, "role": self.user.role})

        response = self.client.post(
            "/api/orders/checkout/instant",
            json={
                "book_id": self.book.id,
                "quantity": 1,
                "shipping_name": "Buyer",
                "shipping_phone": "0900000000",
                "shipping_address": "123 ABC",
                "payment_method": "COD",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["items"][0]["book_id"], self.book.id)
        self.assertEqual(payload["items"][0]["quantity"], 1)
        self.assertEqual(payload["author"], self.book.author)
        self.assertEqual(payload["shipping_name"], "Buyer")
        self.assertGreater(payload["total_amount"], 0)

    def _auth_headers(self):
        import auth as auth_module
        token = auth_module.create_access_token({"sub": self.user.username, "role": self.user.role})
        return {"Authorization": f"Bearer {token}"}

    def test_order_requires_terms_and_recalculates_voucher_and_shipping(self):
        payload = {
            "items": [{"book_id": self.book.id, "quantity": 1}],
            "shipping_name": "Buyer",
            "shipping_phone": "0900000000",
            "shipping_address": "12 Nguyen Trai",
            "shipping_province": "Thành phố Hà Nội",
            "shipping_province_code": "1",
            "shipping_district": "Quận Hoàn Kiếm",
            "shipping_district_code": "2",
            "shipping_ward": "Phường Phúc Tân",
            "shipping_ward_code": "37",
            "shipping_method": "EXPRESS",
            "voucher_code": "TEST20",
            "payment_method": "VIETQR",
            "terms_accepted": False,
        }
        response = self.client.post("/api/orders", json=payload, headers=self._auth_headers())
        self.assertEqual(response.status_code, 400)
        self.assertIn("Điều khoản", response.json()["detail"])

        payload["terms_accepted"] = True
        response = self.client.post("/api/orders", json=payload, headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        order = response.json()
        self.assertEqual(order["payment_status"], "PENDING")
        self.assertEqual(order["shipping_method"], "EXPRESS")
        self.assertEqual(order["discount_amount"], 20000)
        self.assertEqual(order["shipping_fee"], 40000)

    def test_invalid_shipping_and_excess_quantity_are_rejected(self):
        payload = {
            "items": [{"book_id": self.book.id, "quantity": 99}],
            "shipping_name": "Buyer",
            "shipping_phone": "0900000000",
            "shipping_address": "12 Nguyen Trai",
            "shipping_province": "Thành phố Hà Nội",
            "shipping_province_code": "1",
            "shipping_district": "Quận Hoàn Kiếm",
            "shipping_district_code": "2",
            "shipping_ward": "Phường Phúc Tân",
            "shipping_ward_code": "37",
            "shipping_method": "UNKNOWN",
            "payment_method": "COD",
            "terms_accepted": True,
        }
        response = self.client.post("/api/orders", json=payload, headers=self._auth_headers())
        self.assertEqual(response.status_code, 400)
        self.assertIn("kho", response.json()["detail"])

    def test_saved_address_can_be_created_and_selected(self):
        payload = {
            "recipient_name": "Buyer",
            "phone": "0900000000",
            "province": "Thành phố Hà Nội",
            "province_code": "1",
            "district": "Quận Hoàn Kiếm",
            "district_code": "2",
            "ward": "Phường Phúc Tân",
            "ward_code": "37",
            "street": "12 Nguyen Trai",
            "is_default": True,
        }
        response = self.client.post("/api/orders/addresses", json=payload, headers=self._auth_headers())
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["is_default"])


if __name__ == "__main__":
    unittest.main()
