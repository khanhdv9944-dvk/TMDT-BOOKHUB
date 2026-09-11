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
