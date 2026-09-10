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
        order = models.Order(order_code="WF-001", buyer_id=self.buyer.id, total_amount=100000, subtotal_amount=100000, platform_fee_amount=10000, seller_payout_amount=90000, shipping_name="Buyer", shipping_phone="0900000000", shipping_address="HCM", created_at=datetime.utcnow())
        self.db.add(order); self.db.commit(); self.db.refresh(order)
        self.dispute = models.Dispute(dispute_code="DSP-WF-1", order_id=order.id, buyer_id=self.buyer.id, seller_id=self.seller.id, reason="Damaged", description="Damaged book", amount=100000)
        self.payout = models.WithdrawalRequest(seller_id=self.seller.id, amount=100000, bank_name="Test Bank", bank_account_number="1234", bank_account_holder="Seller", status="PENDING")
        self.db.add_all([self.dispute, self.payout]); self.db.commit(); self.db.refresh(self.dispute); self.db.refresh(self.payout)

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


if __name__ == "__main__":
    unittest.main()
