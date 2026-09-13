import unittest

from financial import (
    COMMISSION_RATE,
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
        commission = calculate_commission(gmv)
        self.assertGreaterEqual(gmv, commission)
        self.assertEqual(commission, 5000)

    def test_commission_rate_is_five_percent(self):
        self.assertEqual(COMMISSION_RATE, 0.05)
        self.assertEqual(calculate_commission(310000), 15500)
        self.assertEqual(calculate_commission(100000), 5000)
        self.assertEqual(calculate_commission(1000000), 50000)

    def test_gmv_does_not_multiply_order_with_multiple_items(self):
        self.assertEqual(calculate_gmv([{"status": "DELIVERED", "subtotal_amount": 310000}]), 310000)

    def test_gmv_excludes_cancelled_and_fully_refunded_orders(self):
        orders = [
            {"status": "CANCELED", "subtotal_amount": 100000},
            {"status": "DELIVERED", "subtotal_amount": 100000, "refunded_amount": 100000},
        ]
        self.assertEqual(calculate_gmv(orders), 0)

    def test_partial_refund_reduces_gmv_and_commission(self):
        gmv = calculate_gmv([{"status": "DELIVERED", "subtotal_amount": 310000, "refunded_amount": 100000}])
        self.assertEqual(gmv, 210000)
        self.assertEqual(calculate_commission(gmv), 10500)

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
