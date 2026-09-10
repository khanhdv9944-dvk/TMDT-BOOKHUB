"""Pure marketplace financial calculations shared by API and tests."""
from typing import Iterable


def calculate_gmv(orders: Iterable[dict]) -> float:
    """Sum merchandise values for valid, non-cancelled orders."""
    return sum(
        float(order.get("subtotal_amount") or order.get("total_amount") or 0)
        for order in orders
        if order.get("status") != "CANCELLED"
    )


def calculate_commission(gmv: float, commission_rate: float) -> float:
    return max(float(gmv), 0) * max(float(commission_rate), 0) / 100


def calculate_platform_revenue(
    commission: float,
    advertising_revenue: float = 0,
    other_revenue: float = 0,
    refund_adjustments: float = 0,
) -> float:
    return max(
        float(commission)
        + float(advertising_revenue)
        + float(other_revenue)
        - float(refund_adjustments),
        0,
    )


def calculate_seller_balance(
    seller_sales: float,
    platform_commission: float,
    refunds: float = 0,
    adjustments: float = 0,
) -> float:
    return max(
        float(seller_sales)
        - float(platform_commission)
        - float(refunds)
        - float(adjustments),
        0,
    )


def calculate_available_payout(eligible_balance: float, pending_payouts: float) -> float:
    return max(float(eligible_balance) - float(pending_payouts), 0)
