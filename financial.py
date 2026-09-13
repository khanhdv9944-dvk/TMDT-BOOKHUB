"""Pure marketplace financial calculations shared by API and tests."""
from typing import Iterable


COMMISSION_RATE = 0.05
COMMISSION_RATE_PERCENT = COMMISSION_RATE * 100
EXCLUDED_ORDER_STATUSES = {"CANCELLED", "CANCELED", "REJECTED", "FAILED"}


def order_net_gmv(order: dict, refunded_amount: float = 0) -> float:
    """Return merchandise value remaining after completed refunds."""
    if str(order.get("status", "")).upper() in EXCLUDED_ORDER_STATUSES:
        return 0.0
    merchandise_value = float(order.get("subtotal_amount") or order.get("total_amount") or 0)
    return max(merchandise_value - max(float(refunded_amount or 0), 0), 0)


def calculate_gmv(orders: Iterable[dict]) -> float:
    """Sum merchandise values for valid orders without duplicate joins."""
    return sum(order_net_gmv(order, order.get("refunded_amount", 0)) for order in orders)


def calculate_commission(gmv: float, commission_rate: float = COMMISSION_RATE) -> float:
    return max(float(gmv), 0) * max(float(commission_rate), 0)


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
