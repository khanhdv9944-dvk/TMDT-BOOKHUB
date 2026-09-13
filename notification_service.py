from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
import models

def create_notification(
    db: Session,
    user_id: int,
    title: str,
    message: str,
    type: str,
    reference_id: Optional[int] = None
) -> models.Notification:
    """Tạo một bản ghi thông báo mới cho user_id."""
    notif = models.Notification(
        user_id=user_id,
        title=title,
        message=message,
        type=type,
        reference_id=reference_id,
        is_read=False,
        created_at=datetime.utcnow()
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)
    return notif

def notify_admins_new_book(
    db: Session,
    book: models.Book,
    seller: models.User
) -> List[models.Notification]:
    """
    Luồng 1 (NXB -> Admin):
    Khi NXB gửi duyệt / thêm sách mới -> Tự động gửi thông báo tới tất cả Admin.
    Tiêu đề: 'Sách mới chờ duyệt'
    Nội dung: 'NXB [Tên_NXB] vừa gửi yêu cầu duyệt sách [Tên_Sách]'
    """
    seller_name = seller.shop_name or seller.full_name or seller.username or "NXB"
    admins = db.query(models.User).filter(
        (models.User.role == models.UserRole.ADMIN.value) | (models.User.role == "ADMIN")
    ).all()

    notifications = []
    for admin in admins:
        notif = models.Notification(
            user_id=admin.id,
            title="Sách mới chờ duyệt",
            message=f"NXB {seller_name} vừa gửi yêu cầu duyệt sách '{book.title}'",
            type=models.NotificationType.NEW_BOOK_SUBMITTED.value,
            reference_id=book.id,
            is_read=False,
            created_at=datetime.utcnow()
        )
        db.add(notif)
        notifications.append(notif)

    if notifications:
        db.commit()
        for n in notifications:
            db.refresh(n)

    return notifications

def notify_seller_book_approved(
    db: Session,
    book: models.Book
) -> Optional[models.Notification]:
    """
    Luồng 2 (Admin -> NXB):
    Khi Admin Duyệt (Approve) sách -> Gửi thông báo tới user_id của NXB.
    """
    if not book.seller_id:
        return None

    notif = models.Notification(
        user_id=book.seller_id,
        title="Sách đã được phê duyệt",
        message=f"Cuốn sách '{book.title}' của bạn đã được Admin phê duyệt thành công và mở bán trên sàn!",
        type=models.NotificationType.BOOK_APPROVED.value,
        reference_id=book.id,
        is_read=False,
        created_at=datetime.utcnow()
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)
    return notif

def notify_seller_book_rejected(
    db: Session,
    book: models.Book,
    reason: Optional[str] = None
) -> Optional[models.Notification]:
    """
    Luồng 2 (Admin -> NXB):
    Khi Admin Từ chối (Reject) sách -> Gửi thông báo tới user_id của NXB kèm lý do.
    """
    if not book.seller_id:
        return None

    reason_str = f" Lý do: {reason}" if reason else ""
    notif = models.Notification(
        user_id=book.seller_id,
        title="Yêu cầu duyệt sách bị từ chối",
        message=f"Cuốn sách '{book.title}' của bạn đã bị từ chối duyệt.{reason_str}",
        type=models.NotificationType.BOOK_REJECTED.value,
        reference_id=book.id,
        is_read=False,
        created_at=datetime.utcnow()
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)
    return notif


# =============================================================================
# LUỒNG THÔNG BÁO TIẾN TRÌNH ĐƠN HÀNG & ĐÁNH GIÁ (ORDER & REVIEW LIFECYCLE)
# =============================================================================

def _get_order_seller_ids(order: models.Order) -> List[int]:
    """Lấy danh sách các seller_id duy nhất từ các item trong đơn hàng."""
    seller_ids = set()
    for item in (order.items or []):
        if item.seller_id:
            seller_ids.add(item.seller_id)
    return list(seller_ids)

def notify_order_created(
    db: Session,
    order: models.Order,
    buyer: models.User
) -> List[models.Notification]:
    """
    📦 Giai đoạn 1: Khách hàng vừa đặt hàng xong
    - Gửi Khách hàng: "Đơn hàng #[Mã_đơn] đã được đặt thành công. NXB đang tiếp nhận xử lý."
    - Gửi NXB: "Bạn có đơn hàng mới #[Mã_đơn] từ khách hàng [Tên_KH]. Hãy chuẩn bị đóng gói."
    """
    notifications = []
    buyer_name = buyer.full_name or buyer.username or order.shipping_name or "Khách hàng"

    # 1. Gửi Khách hàng
    if order.buyer_id:
        notif_buyer = models.Notification(
            user_id=order.buyer_id,
            title="Đặt hàng thành công",
            message=f"Đơn hàng #{order.order_code} đã được đặt thành công. NXB đang tiếp nhận xử lý.",
            type=models.NotificationType.ORDER_CREATED.value,
            reference_id=order.id,
            is_read=False,
            created_at=datetime.utcnow()
        )
        db.add(notif_buyer)
        notifications.append(notif_buyer)

    # 2. Gửi NXB
    seller_ids = _get_order_seller_ids(order)
    for seller_id in seller_ids:
        notif_seller = models.Notification(
            user_id=seller_id,
            title="Đơn hàng mới",
            message=f"Bạn có đơn hàng mới #{order.order_code} từ khách hàng {buyer_name}. Hãy chuẩn bị đóng gói.",
            type=models.NotificationType.ORDER_CREATED.value,
            reference_id=order.id,
            is_read=False,
            created_at=datetime.utcnow()
        )
        db.add(notif_seller)
        notifications.append(notif_seller)

    if notifications:
        db.commit()
        for n in notifications:
            db.refresh(n)

    return notifications


def notify_order_packing(
    db: Session,
    order: models.Order
) -> Optional[models.Notification]:
    """
    📦 Giai đoạn 1: NXB bấm "Xác nhận & Đóng gói"
    - Gửi Khách hàng: "Đơn hàng #[Mã_đơn] đang được NXB đóng gói và chuẩn bị giao cho đơn vị vận chuyển."
    """
    if not order.buyer_id:
        return None

    notif = models.Notification(
        user_id=order.buyer_id,
        title="Đơn hàng đang đóng gói",
        message=f"Đơn hàng #{order.order_code} đang được NXB đóng gói và chuẩn bị giao cho đơn vị vận chuyển.",
        type=models.NotificationType.ORDER_PACKING.value,
        reference_id=order.id,
        is_read=False,
        created_at=datetime.utcnow()
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)
    return notif


def notify_order_shipping(
    db: Session,
    order: models.Order,
    carrier: Optional[str] = None,
    tracking_code: Optional[str] = None
) -> List[models.Notification]:
    """
    🚚 Giai đoạn 2: NXB bàn giao cho đơn vị vận chuyển
    - Gửi Khách hàng: "Đơn hàng #[Mã_đơn] đã được giao cho đơn vị vận chuyển [Tên_NVC]. Mã vận đơn: [Mã_VD]."
    - Gửi NXB: "Đơn hàng #[Mã_đơn] đã rời kho và đang trên đường vận chuyển."
    """
    notifications = []
    carrier_name = carrier or order.shipping_carrier or "Giao Hàng Nhanh (GHN Express)"
    tracking_num = tracking_code or getattr(order, 'tracking_number', None) or f"VN-{order.id:06d}-GHN"

    # 1. Gửi Khách hàng
    if order.buyer_id:
        notif_buyer = models.Notification(
            user_id=order.buyer_id,
            title="Đơn hàng đã bàn giao vận chuyển",
            message=f"Đơn hàng #{order.order_code} đã được giao cho đơn vị vận chuyển {carrier_name}. Mã vận đơn: {tracking_num}.",
            type=models.NotificationType.ORDER_SHIPPING.value,
            reference_id=order.id,
            is_read=False,
            created_at=datetime.utcnow()
        )
        db.add(notif_buyer)
        notifications.append(notif_buyer)

    # 2. Gửi NXB
    seller_ids = _get_order_seller_ids(order)
    for seller_id in seller_ids:
        notif_seller = models.Notification(
            user_id=seller_id,
            title="Đơn hàng đã rời kho",
            message=f"Đơn hàng #{order.order_code} đã rời kho và đang trên đường vận chuyển.",
            type=models.NotificationType.ORDER_SHIPPING.value,
            reference_id=order.id,
            is_read=False,
            created_at=datetime.utcnow()
        )
        db.add(notif_seller)
        notifications.append(notif_seller)

    if notifications:
        db.commit()
        for n in notifications:
            db.refresh(n)

    return notifications


def notify_order_out_for_delivery(
    db: Session,
    order: models.Order
) -> Optional[models.Notification]:
    """
    🚚 Giai đoạn 2: Shipper báo "Đang giao hàng đến nơi"
    - Gửi Khách hàng: "Đơn hàng #[Mã_đơn] đang trên đường giao đến bạn. Vui lòng giữ liên lạc điện thoại."
    """
    if not order.buyer_id:
        return None

    notif = models.Notification(
        user_id=order.buyer_id,
        title="Đơn hàng đang trên đường giao đến bạn",
        message=f"Đơn hàng #{order.order_code} đang trên đường giao đến bạn. Vui lòng giữ liên lạc điện thoại.",
        type=models.NotificationType.ORDER_OUT_FOR_DELIVERY.value,
        reference_id=order.id,
        is_read=False,
        created_at=datetime.utcnow()
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)
    return notif


def notify_order_delivered(
    db: Session,
    order: models.Order,
    buyer: Optional[models.User] = None
) -> List[models.Notification]:
    """
    ✅ Giai đoạn 3: Xác nhận Nhận hàng (Khách hàng thao tác / Shipper hoàn tất)
    - Gửi Khách hàng: "Cảm ơn bạn đã xác nhận nhận hàng! Hãy để lại đánh giá cho sản phẩm nhé."
    - Gửi NXB: "Khách hàng [Tên_KH] đã xác nhận nhận thành công đơn hàng #[Mã_đơn]. Tiền đơn hàng đã chuyển vào doanh thu."
    """
    notifications = []
    if buyer:
        buyer_name = buyer.full_name or buyer.username or order.shipping_name or "Khách hàng"
    elif order.buyer:
        buyer_name = order.buyer.full_name or order.buyer.username or order.shipping_name or "Khách hàng"
    else:
        buyer_name = order.shipping_name or "Khách hàng"

    # 1. Gửi Khách hàng
    if order.buyer_id:
        notif_buyer = models.Notification(
            user_id=order.buyer_id,
            title="Đã nhận hàng thành công",
            message=f"Cảm ơn bạn đã xác nhận nhận hàng! Hãy để lại đánh giá cho sản phẩm nhé.",
            type=models.NotificationType.ORDER_DELIVERED.value,
            reference_id=order.id,
            is_read=False,
            created_at=datetime.utcnow()
        )
        db.add(notif_buyer)
        notifications.append(notif_buyer)

    # 2. Gửi NXB
    seller_ids = _get_order_seller_ids(order)
    for seller_id in seller_ids:
        notif_seller = models.Notification(
            user_id=seller_id,
            title="Khách hàng đã nhận hàng",
            message=f"Khách hàng {buyer_name} đã xác nhận nhận thành công đơn hàng #{order.order_code}. Tiền đơn hàng đã chuyển vào doanh thu.",
            type=models.NotificationType.ORDER_DELIVERED.value,
            reference_id=order.id,
            is_read=False,
            created_at=datetime.utcnow()
        )
        db.add(notif_seller)
        notifications.append(notif_seller)

    if notifications:
        db.commit()
        for n in notifications:
            db.refresh(n)

    return notifications


def notify_order_reviewed(
    db: Session,
    order: models.Order,
    review: models.Review,
    buyer: models.User,
    seller_id: Optional[int] = None
) -> List[models.Notification]:
    """
    ⭐ Giai đoạn 4: Đánh giá Sản phẩm
    - Gửi Khách hàng: "Cảm ơn bạn đã đánh giá đơn hàng #[Mã_đơn]. NXB đã nhận được phản hồi của bạn."
    - Gửi NXB: "Khách hàng [Tên_KH] vừa đánh giá ⭐⭐⭐⭐⭐ cho đơn hàng #[Mã_đơn]: '[Nội dung bình luận]'."
    """
    notifications = []
    buyer_name = buyer.full_name or buyer.username or "Khách hàng"
    stars_count = max(1, min(5, int(review.rating)))
    stars_str = "⭐" * stars_count
    comment_content = (review.content or "").strip()

    # 1. Gửi Khách hàng
    if order.buyer_id:
        notif_buyer = models.Notification(
            user_id=order.buyer_id,
            title="Đánh giá thành công",
            message=f"Cảm ơn bạn đã đánh giá đơn hàng #{order.order_code}. NXB đã nhận được phản hồi của bạn.",
            type=models.NotificationType.ORDER_REVIEWED.value,
            reference_id=order.id,
            is_read=False,
            created_at=datetime.utcnow()
        )
        db.add(notif_buyer)
        notifications.append(notif_buyer)

    # 2. Gửi NXB
    target_seller_id = seller_id or review.seller_id
    if not target_seller_id and review.product and review.product.seller_id:
        target_seller_id = review.product.seller_id

    if target_seller_id:
        notif_seller = models.Notification(
            user_id=target_seller_id,
            title="Đánh giá mới từ khách hàng",
            message=f"Khách hàng {buyer_name} vừa đánh giá {stars_str} cho đơn hàng #{order.order_code}: '{comment_content}'.",
            type=models.NotificationType.ORDER_REVIEWED.value,
            reference_id=order.id,
            is_read=False,
            created_at=datetime.utcnow()
        )
        db.add(notif_seller)
        notifications.append(notif_seller)

    if notifications:
        db.commit()
        for n in notifications:
            db.refresh(n)

    return notifications

