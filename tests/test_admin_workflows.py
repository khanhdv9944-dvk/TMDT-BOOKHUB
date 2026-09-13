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


class AdminWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        database.engine = self.engine
        database.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        models.Base.metadata.create_all(bind=self.engine)
        self.db = database.SessionLocal()
        self.admin = models.User(username="workflow_admin", email="workflow_admin@test.local", hashed_password=auth.get_password_hash("pw"), full_name="Admin", role="ADMIN", status="ACTIVE")
        self.seller = models.User(username="workflow_seller", email="workflow_seller@test.local", hashed_password=auth.get_password_hash("pw"), full_name="Seller", role="SELLER", status="ACTIVE", seller_balance=500000)
        self.buyer = models.User(username="workflow_buyer", email="workflow_buyer@test.local", hashed_password=auth.get_password_hash("pw"), full_name="Buyer", role="BUYER", status="ACTIVE")
        self.db.add_all([self.admin, self.seller, self.buyer])
        self.db.commit()
        self.db.refresh(self.admin); self.db.refresh(self.seller); self.db.refresh(self.buyer)
        order = models.Order(order_code="WF-001", buyer_id=self.buyer.id, total_amount=100000, subtotal_amount=100000, platform_fee_percent=5.0, platform_fee_amount=5000, seller_payout_amount=95000, shipping_name="Buyer", shipping_phone="0900000000", shipping_address="HCM", created_at=datetime.utcnow())
        self.db.add(order); self.db.commit(); self.db.refresh(order)
        self.dispute = models.Dispute(dispute_code="DSP-WF-1", order_id=order.id, buyer_id=self.buyer.id, seller_id=self.seller.id, reason="Damaged", description="Damaged book", amount=100000)
        self.payout = models.WithdrawalRequest(seller_id=self.seller.id, amount=100000, bank_name="Test Bank", bank_account_number="1234", bank_account_holder="Seller", status="PENDING")
        self.db.add_all([self.dispute, self.payout]); self.db.commit(); self.db.refresh(self.dispute); self.db.refresh(self.payout)

        self.category = models.Category(name="Workflow Books", slug="workflow-books")
        self.db.add(self.category); self.db.commit(); self.db.refresh(self.category)
        self.pending_book = models.Book(
            seller_id=self.seller.id,
            category_id=self.category.id,
            title="Pending workflow book",
            author="Workflow author",
            price=100000,
            stock=5,
            status=models.BookStatus.PENDING.value,
            is_visible=True,
        )
        self.db.add(self.pending_book); self.db.commit(); self.db.refresh(self.pending_book)

        def override_get_db():
            db = database.SessionLocal()
            try:
                yield db
            finally:
                db.close()
        app.dependency_overrides[database.get_db] = override_get_db
        self.client = TestClient(app)
        token = auth.create_access_token({"sub": self.admin.username, "role": "ADMIN"})
        self.headers = {"Authorization": f"Bearer {token}"}

    def tearDown(self):
        app.dependency_overrides.clear()
        self.db.close()

    def test_admin_can_resolve_dispute_and_persist(self):
        response = self.client.post(f"/api/admin/disputes/{self.dispute.id}/resolve", json={"decision": "REFUND_BUYER", "note": "Refund approved"}, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "RESOLVED")
        self.db.expire_all()
        saved = self.db.get(models.Dispute, self.dispute.id)
        self.assertEqual(saved.admin_decision, "REFUND_BUYER")

    def test_admin_approval_moves_book_out_of_pending_and_publishes_it(self):
        pending = self.client.get("/api/admin/books/pending", headers=self.headers)
        self.assertEqual(pending.status_code, 200)
        self.assertIn(self.pending_book.id, [book["id"] for book in pending.json()])

        response = self.client.post(f"/api/admin/books/{self.pending_book.id}/approve", headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        self.db.expire_all()
        saved = self.db.get(models.Book, self.pending_book.id)
        self.assertEqual(saved.status, models.BookStatus.APPROVED.value)
        self.assertTrue(saved.is_visible)
        pending_after = self.client.get("/api/admin/books/pending", headers=self.headers)
        self.assertNotIn(self.pending_book.id, [book["id"] for book in pending_after.json()])

    def test_admin_rejection_keeps_book_hidden_and_records_reason(self):
        response = self.client.post(
            f"/api/admin/books/{self.pending_book.id}/reject",
            json={"reason": "Thiếu thông tin xuất bản"},
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.db.expire_all()
        saved = self.db.get(models.Book, self.pending_book.id)
        self.assertEqual(saved.status, models.BookStatus.REJECTED.value)
        self.assertFalse(saved.is_visible)
        self.assertEqual(saved.rejection_reason, "Thiếu thông tin xuất bản")

    def test_non_admin_cannot_approve_book(self):
        token = auth.create_access_token({"sub": self.seller.username, "role": "SELLER"})
        response = self.client.post(
            f"/api/admin/books/{self.pending_book.id}/approve",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_payout_approval_creates_pending_transaction(self):
        response = self.client.post(f"/api/admin/payouts/{self.payout.id}/approve", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "APPROVED")
        transaction = self.db.query(models.Transaction).filter_by(payout_id=self.payout.id).one()
        self.assertEqual(transaction.status, "PENDING")
        self.assertEqual(self.db.get(models.User, self.seller.id).seller_balance, 400000)

    def test_non_admin_cannot_access_admin_workflow(self):
        token = auth.create_access_token({"sub": self.seller.username, "role": "SELLER"})
        response = self.client.get("/api/admin/payouts", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(response.status_code, 403)

    def test_admin_return_list_endpoint_exists(self):
        return_request = models.ReturnRequest(
            order_id=1,
            user_id=self.buyer.id,
            status=models.ReturnRequestStatus.PENDING.value,
            reason=models.ReturnReason.PRODUCT_DEFECT.value,
            refund_amount=50000,
            description="Sách bị lỗi"
        )
        self.db.add(return_request)
        self.db.commit()
        self.db.refresh(return_request)

        response = self.client.get("/api/admin/returns", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIsInstance(payload, list)
        self.assertGreaterEqual(len(payload), 1)
        self.assertEqual(payload[0]["order_id"], 1)

    def test_seller_return_list_endpoint_exists(self):
        return_request = models.ReturnRequest(
            order_id=1,
            user_id=self.buyer.id,
            status=models.ReturnRequestStatus.PENDING.value,
            reason=models.ReturnReason.PRODUCT_DEFECT.value,
            refund_amount=50000,
            description="Sách bị lỗi"
        )
        self.db.add(return_request)
        self.db.commit()
        self.db.refresh(return_request)

        token = auth.create_access_token({"sub": self.seller.username, "role": "SELLER"})
        response = self.client.get("/api/seller/returns", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIsInstance(payload, list)

    def test_seller_upload_document_and_admin_preview(self):
        seller_token = auth.create_access_token({"sub": self.seller.username, "role": "SELLER"})
        upload_response = self.client.post(
            "/api/auth/seller/upload-document",
            files={"file": ("license.pdf", b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF", "application/pdf")},
            data={"document_type": "BUSINESS_LICENSE"},
            headers={"Authorization": f"Bearer {seller_token}"}
        )
        self.assertEqual(upload_response.status_code, 200, upload_response.text)
        doc_id = upload_response.json()["id"]

        preview_response = self.client.get(f"/api/admin/documents/{doc_id}/preview", headers=self.headers)
        self.assertEqual(preview_response.status_code, 200)
        self.assertTrue(preview_response.json()["available"])


if __name__ == "__main__":
    unittest.main()
