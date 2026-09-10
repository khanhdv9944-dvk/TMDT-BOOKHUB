import unittest

from financial import (
    calculate_available_payout,
    calculate_commission,
    calculate_gmv,
    calculate_platform_revenue,
    calculate_seller_balance,
)


class FinancialCalculationTests(unittest.TestCase):
    def test_gmv_excludes_cancelled_orders(self):
        orders = [
            {"status": "DELIVERED", "subtotal_amount": 100000},
            {"status": "CANCELLED", "subtotal_amount": 50000},
        ]
        self.assertEqual(calculate_gmv(orders), 100000)

    def test_commission_is_bounded_by_gmv(self):
        gmv = calculate_gmv([{"status": "DELIVERED", "subtotal_amount": 100000}])
        commission = calculate_commission(gmv, 10)
        self.assertGreaterEqual(gmv, commission)
        self.assertEqual(commission, 10000)

    def test_refund_reduces_platform_revenue(self):
        self.assertEqual(calculate_platform_revenue(100000, 30000, 20000, 25000), 125000)

    def test_seller_balance_and_available_payout(self):
        balance = calculate_seller_balance(1000000, 100000, 50000, 25000)
        self.assertEqual(balance, 825000)
        self.assertEqual(calculate_available_payout(balance, 200000), 625000)

    def test_available_payout_cannot_be_negative(self):
        self.assertEqual(calculate_available_payout(100000, 150000), 0)


if __name__ == "__main__":
    unittest.main()
