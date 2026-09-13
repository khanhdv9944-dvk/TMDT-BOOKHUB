import unittest
from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import auth
import database
import models
from main import app


class ReviewWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        database.engine = self.engine
        database.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        models.Base.metadata.create_all(bind=self.engine)
        self.db = database.SessionLocal()

        self.category = models.Category(name="Review Test", slug="review-test")
        self.db.add(self.category)
        self.db.commit()
        self.db.refresh(self.category)

        self.buyer = models.User(
            username="buyer_review",
            email="buyer_review@test.local",
            hashed_password=auth.get_password_hash("pw"),
            full_name="Buyer Review",
            role=models.UserRole.BUYER.value,
            status=models.UserStatus.ACTIVE.value,
            phone="0901000000",
            address="HCM",
        )
        self.seller = models.User(
            username="seller_review",
            email="seller_review@test.local",
            hashed_password=auth.get_password_hash("pw"),
            full_name="Seller Review",
            role=models.UserRole.SELLER.value,
            status=models.UserStatus.ACTIVE.value,
            shop_name="Seller Review Shop",
        )
        self.admin = models.User(
            username="admin_review",
            email="admin_review@test.local",
            hashed_password=auth.get_password_hash("pw"),
            full_name="Admin Review",
            role=models.UserRole.ADMIN.value,
            status=models.UserStatus.ACTIVE.value,
        )
        self.db.add_all([self.buyer, self.seller, self.admin])
        self.db.commit()
        self.db.refresh(self.buyer)
        self.db.refresh(self.seller)
        self.db.refresh(self.admin)

        self.book = models.Book(
            seller_id=self.seller.id,
            category_id=self.category.id,
            title="Review Book",
            author="Author",
            price=120000,
            discount_price=100000,
            stock=10,
            status=models.BookStatus.APPROVED.value,
            sold_count=0,
            rating=5.0,
        )
        self.db.add(self.book)
        self.db.commit()
        self.db.refresh(self.book)

        self.order = models.Order(
            order_code="REV-001",
            buyer_id=self.buyer.id,
            total_amount=100000,
            platform_fee_percent=5.0,
            platform_fee_amount=5000,
            seller_payout_amount=90000,
            shipping_name="Buyer Review",
            shipping_phone="0901000000",
            shipping_address="HCM",
            shipping_method="STANDARD",
            shipping_fee=30000,
            subtotal_amount=100000,
            discount_amount=0,
            payment_method="COD",
            payment_status=models.PaymentStatus.PAID.value,
            status=models.OrderStatus.DELIVERED.value,
            tracking_step=4,
            created_at=datetime.utcnow(),
        )
        self.db.add(self.order)
        self.db.commit()
        self.db.refresh(self.order)

        self.order_item = models.OrderItem(
            order_id=self.order.id,
            book_id=self.book.id,
            seller_id=self.seller.id,
            quantity=1,
            price=100000,
            book_title=self.book.title,
            book_cover=self.book.cover_image,
        )
        self.db.add(self.order_item)
        self.db.commit()
        self.db.refresh(self.order_item)

        def override_get_db():
            db = database.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[database.get_db] = override_get_db
        app.dependency_overrides[auth.get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.db.close()

    def _buyer_headers(self):
        token = auth.create_access_token({"sub": self.buyer.username, "role": self.buyer.role})
        return {"Authorization": f"Bearer {token}"}

    def _seller_headers(self):
        token = auth.create_access_token({"sub": self.seller.username, "role": self.seller.role})
        return {"Authorization": f"Bearer {token}"}

    def _admin_headers(self):
        token = auth.create_access_token({"sub": self.admin.username, "role": self.admin.role})
        return {"Authorization": f"Bearer {token}"}

    def test_customer_can_submit_review_and_duplicate_is_blocked(self):
        response = self.client.post(
            "/api/reviews",
            json={
                "order_id": self.order.id,
                "order_item_id": self.order_item.id,
                "product_id": self.book.id,
                "rating": 5,
                "content": "Sách giao rất nhanh, chất lượng tốt",
                "images": ["https://example.com/review1.jpg"],
            },
            headers=self._buyer_headers(),
        )
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertEqual(data["rating"], 5)
        self.assertEqual(data["status"], "REVIEWED")
        self.assertEqual(len(data["images"]), 1)

        duplicate = self.client.post(
            "/api/reviews",
            json={
                "order_id": self.order.id,
                "order_item_id": self.order_item.id,
                "product_id": self.book.id,
                "rating": 4,
                "content": "Lần 2",
                "images": [],
            },
            headers=self._buyer_headers(),
        )
        self.assertEqual(duplicate.status_code, 400)

    def test_seller_can_reply_and_admin_can_hide_review(self):
        create = self.client.post(
            "/api/reviews",
            json={
                "order_id": self.order.id,
                "order_item_id": self.order_item.id,
                "product_id": self.book.id,
                "rating": 4,
                "content": "Đóng gói tốt",
                "images": [],
            },
            headers=self._buyer_headers(),
        )
        review_id = create.json()["id"]

        reply = self.client.post(
            f"/api/reviews/{review_id}/seller-reply",
            json={"content": "Cảm ơn bạn đã ủng hộ shop."},
            headers=self._seller_headers(),
        )
        self.assertEqual(reply.status_code, 200)
        self.assertIn("Cảm ơn", reply.json()["reply"]["content"])

        hide = self.client.patch(
            f"/api/admin/reviews/{review_id}/hide",
            headers=self._admin_headers(),
        )
        self.assertEqual(hide.status_code, 200)
        self.assertEqual(hide.json()["status"], "HIDDEN")

        product_reviews = self.client.get(f"/api/reviews/product/{self.book.id}")
        self.assertEqual(product_reviews.status_code, 200)
        self.assertGreaterEqual(product_reviews.json()["total_reviews"], 0)
