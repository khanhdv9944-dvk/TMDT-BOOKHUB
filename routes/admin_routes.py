from datetime import datetime
from typing import List, Optional
import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from database import get_db
import models, schemas, auth
import notification_service
from financial import COMMISSION_RATE_PERCENT, calculate_commission, order_net_gmv

router = APIRouter(prefix="/api/admin", tags=["Admin Portal"])

@router.get("/financial-overview")
def get_platform_financial_overview(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.UserRole.ADMIN.value]))
):
    """Báo cáo GMV và phí hoa hồng thực tế từ các đơn hàng hợp lệ."""
    orders = db.query(models.Order).all()
    refunded_by_order = {}
    refunded_requests = db.query(models.ReturnRequest).filter(
        models.ReturnRequest.status == models.ReturnRequestStatus.REFUNDED.value
    ).all()
    for request in refunded_requests:
        refunded_by_order[request.order_id] = refunded_by_order.get(request.order_id, 0.0) + (request.refund_amount or 0.0)

    order_values = [
        order_net_gmv(
            {"status": order.status, "subtotal_amount": order.subtotal_amount, "total_amount": order.total_amount},
            refunded_by_order.get(order.id, 0.0),
        )
        for order in orders
    ]
    total_gmv = sum(order_values)
    total_commission_earned = sum(calculate_commission(value) for value in order_values)
    total_orders = sum(1 for value in order_values if value > 0)
    successful_orders = sum(1 for order, value in zip(orders, order_values) if order.status == models.OrderStatus.DELIVERED.value and value > 0)
    cancelled_orders = sum(1 for order in orders if str(order.status).upper() in {"CANCELLED", "CANCELED"})
    refunded_orders = sum(1 for order in orders if refunded_by_order.get(order.id, 0.0) > 0)
    returned_orders = db.query(models.Order).filter(models.Order.return_status != "NONE").count()
    total_refunds = sum(refunded_by_order.values())

    # 2. Doanh thu từ Quảng Cáo vị trí nổi bật (Ads Revenue)
    total_ad_revenue = db.query(func.sum(models.AdCampaign.fee_paid)).scalar() or 0.0
    total_ad_campaigns = db.query(models.AdCampaign).count()

    # 3. Doanh thu từ Bán gói VIP Membership (Ebook / Audiobook)
    total_vip_revenue = db.query(func.sum(models.VipSubscription.price)).scalar() or 0.0
    total_vip_members = db.query(models.VipSubscription).count()

    # This metric is intentionally commission-only. Ads and VIP are separate streams.
    total_platform_revenue = total_commission_earned

    # Thống kê tổng số lượng thực thể
    total_users = db.query(models.User).count()
    total_sellers = db.query(models.User).filter(models.User.role == models.UserRole.SELLER.value).count()
    pending_sellers = db.query(models.User).filter(models.User.status == models.UserStatus.PENDING_SELLER_APPROVAL.value).count()
    pending_books = db.query(models.Book).filter(models.Book.status == models.BookStatus.PENDING.value).count()
    total_books = db.query(models.Book).count()
    active_books = db.query(models.Book).filter(models.Book.status == models.BookStatus.APPROVED.value, models.Book.is_visible.is_(True)).count()
    pending_disputes = db.query(models.Dispute).filter(models.Dispute.status.in_(["OPEN", "UNDER_REVIEW", "WAITING_SELLER", "WAITING_BUYER"])).count()
    pending_payouts = db.query(models.WithdrawalRequest).filter(models.WithdrawalRequest.status == "PENDING").count()
    total_payouts = db.query(models.WithdrawalRequest).count()
    total_disputes = db.query(models.Dispute).count()
    total_documents = db.query(models.Document).count()
    order_status_counts = {status_value: count for status_value, count in db.query(models.Order.status, func.count(models.Order.id)).group_by(models.Order.status).all()}

    return {
        "financial_summary": {
            "gmv": total_gmv,
            "commission_revenue": total_commission_earned,
            "advertising_revenue": total_ad_revenue,
            "other_revenue": total_vip_revenue,
            "platform_revenue": total_platform_revenue,
            # Kept for existing clients; this is revenue, not net profit.
            "total_platform_profit": total_platform_revenue,
            "total_gmv_gross": total_gmv,
            "revenue_streams": [
                {
                    "name": f"Phí hoa hồng dịch vụ bán sách ({COMMISSION_RATE_PERCENT:.0f}%)",
                    "code": "COMMISSION_FEE",
                    "amount": total_commission_earned,
                    "percent_share": round((total_commission_earned / total_platform_revenue * 100), 1) if total_platform_revenue > 0 else 0,
                    "description": "Phí hoa hồng thực tế trên đơn hàng hợp lệ"
                },
                {
                    "name": "Doanh thu Quảng cáo vị trí Top (Book Ads)",
                    "code": "AD_REVENUE",
                    "amount": total_ad_revenue,
                    "percent_share": round((total_ad_revenue / total_platform_revenue * 100), 1) if total_platform_revenue > 0 else 0,
                    "description": "Thu phí từ NXB muốn đưa sách lên đầu trang chủ"
                },
                {
                    "name": "Bán gói Hội viên VIP Đọc sách Online",
                    "code": "VIP_SUBSCRIPTION",
                    "amount": total_vip_revenue,
                    "percent_share": round((total_vip_revenue / total_platform_revenue * 100), 1) if total_platform_revenue > 0 else 0,
                    "description": "Thu phí định kỳ độc giả đọc toàn bộ Ebook/Sách nói không giới hạn"
                }
            ]
        },
        "stats": {
            "total_orders": total_orders,
            "successful_orders": successful_orders,
            "cancelled_orders": cancelled_orders,
            "returned_orders": returned_orders,
            "refunded_orders": refunded_orders,
            "total_refunds": total_refunds,
            "total_users": total_users,
            "total_sellers": total_sellers,
            "pending_sellers": pending_sellers,
            "pending_books": pending_books,
            "total_vip_members": total_vip_members,
            "total_ad_campaigns": total_ad_campaigns
            ,"total_books": total_books
            ,"active_books": active_books
            ,"total_disputes": total_disputes
            ,"pending_disputes": pending_disputes
            ,"total_payouts": total_payouts
            ,"pending_payouts": pending_payouts
            ,"total_documents": total_documents
            ,"order_status_counts": order_status_counts
        }
    }


@router.get("/orders")
def list_admin_orders(db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_role([models.UserRole.ADMIN.value]))):
    orders = db.query(models.Order).order_by(models.Order.created_at.desc()).all()
    return [{
        "id": order.id,
        "order_code": order.order_code,
        "buyer": order.buyer.full_name if order.buyer else f"User #{order.buyer_id}",
        "seller": order.items[0].seller.shop_name if order.items and order.items[0].seller else "Nhiều seller",
        "items": len(order.items),
        "total": order.total_amount,
        "payment": order.payment_status,
        "status": order.status,
        "created_at": order.created_at,
    } for order in orders]


@router.get("/orders/{order_id}")
def get_admin_order(order_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_role([models.UserRole.ADMIN.value]))):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng")
    return {
        "id": order.id,
        "order_code": order.order_code,
        "buyer": order.buyer.full_name if order.buyer else f"User #{order.buyer_id}",
        "seller": order.items[0].seller.shop_name if order.items and order.items[0].seller else "Nhiều seller",
        "items": [{"title": item.book_title, "quantity": item.quantity, "price": item.price} for item in order.items],
        "total": order.total_amount,
        "payment": order.payment_status,
        "status": order.status,
        "shipping": order.shipping_address,
        "created_at": order.created_at,
    }


@router.get("/transactions")
def list_admin_transactions(db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_role([models.UserRole.ADMIN.value]))):
    transactions = db.query(models.Transaction).order_by(models.Transaction.created_at.desc()).all()
    return [{
        "id": item.id,
        "transaction_code": item.transaction_code,
        "seller_id": item.seller_id,
        "transaction_type": item.transaction_type,
        "gross": item.gross_amount,
        "fee": item.fee_amount,
        "net": item.net_amount,
        "status": item.status,
        "created_at": item.created_at,
    } for item in transactions]

@router.get("/sellers/pending", response_model=List[schemas.UserOut])
def get_pending_sellers(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.UserRole.ADMIN.value]))
):
    """Lấy danh sách các Tiệm sách / NXB mới đăng ký cần xét duyệt uy tín (chống sách giả)"""
    return db.query(models.User).filter(
        models.User.role == models.UserRole.SELLER.value,
        models.User.status == models.UserStatus.PENDING_SELLER_APPROVAL.value
    ).all()


@router.get("/sellers/{seller_id}", response_model=schemas.UserOut)
def get_seller(seller_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_role([models.UserRole.ADMIN.value]))):
    seller = db.query(models.User).filter(models.User.id == seller_id, models.User.role == models.UserRole.SELLER.value).first()
    if not seller:
        raise HTTPException(status_code=404, detail="Không tìm thấy seller")
    return seller

@router.post("/sellers/{seller_id}/approve")
def approve_seller(
    seller_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.UserRole.ADMIN.value]))
):
    seller = db.query(models.User).filter(models.User.id == seller_id).first()
    if not seller:
        raise HTTPException(status_code=404, detail="Không tìm thấy NXB")
    
    seller.status = models.UserStatus.ACTIVE.value
    db.commit()
    return {"message": f"Đã phê duyệt uy tín NXB '{seller.shop_name or seller.full_name}' chính thức hoạt động trên sàn!"}

@router.post("/sellers/{seller_id}/reject")
def reject_seller(
    seller_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.UserRole.ADMIN.value]))
):
    seller = db.query(models.User).filter(models.User.id == seller_id).first()
    if not seller:
        raise HTTPException(status_code=404, detail="Không tìm thấy NXB")
    
    seller.status = models.UserStatus.BANNED.value
    seller.rejection_reason = "Hồ sơ seller bị từ chối bởi Admin"
    seller.rejected_at = datetime.utcnow()
    seller.rejected_by = current_user.id
    db.commit()
    return {"message": f"Đã từ chối cấp phép NXB '{seller.shop_name or seller.full_name}' do không đủ tiêu chuẩn chống sách giả"}

@router.get("/books/pending", response_model=List[schemas.BookOut])
def get_pending_books(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.UserRole.ADMIN.value]))
):
    """Lấy danh sách sách mới cần Admin duyệt trước khi cho xuất hiện trên trang chủ"""
    books = db.query(models.Book).filter(
        models.Book.status == models.BookStatus.PENDING.value
    ).order_by(models.Book.created_at.desc()).all()

    results = []
    for b in books:
        results.append({
            "id": b.id,
            "seller_id": b.seller_id,
            "category_id": b.category_id,
            "title": b.title,
            "author": b.author,
            "publisher": b.publisher,
            "price": b.price,
            "discount_price": b.discount_price,
            "stock": b.stock,
            "cover_image": b.cover_image,
            "description": b.description,
            "book_format": b.book_format or "PAPER",
            "cover_type": b.cover_type or "SOFT",
            "vip_eligible": b.vip_eligible or False,
            "isbn": b.isbn,
            "translator": b.translator,
            "page_count": b.page_count,
            "publication_year": b.publication_year,
            "language": b.language or "Tiếng Việt",
            "preview_file_url": b.preview_file_url,
            "sample_content": b.sample_content,
            "full_ebook_content": b.full_ebook_content,
            "status": b.status,
            "is_featured_ad": b.is_featured_ad or False,
            "sold_count": b.sold_count or 0,
            "rating": b.rating or 5.0,
            "created_at": b.created_at,
            "seller_shop_name": b.seller.shop_name if b.seller and b.seller.shop_name else (b.seller.full_name if b.seller else "NXB"),
            "category_name": b.category.name if b.category else "Chưa phân loại",
            "is_visible": getattr(b, "is_visible", True),
            "is_out_of_stock": getattr(b, "is_out_of_stock", False),
            "rejection_reason": getattr(b, "rejection_reason", None)
        })
    return results


@router.get("/books/{book_id}", response_model=schemas.BookOut)
def get_admin_book(book_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_role([models.UserRole.ADMIN.value]))):
    book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Không tìm thấy sách")
    return {
        **{field: getattr(book, field) for field in ["id", "seller_id", "category_id", "title", "author", "publisher", "price", "discount_price", "stock", "cover_image", "description", "book_format", "cover_type", "vip_eligible", "isbn", "translator", "page_count", "publication_year", "language", "preview_file_url", "sample_content", "full_ebook_content", "status", "is_featured_ad", "sold_count", "rating", "created_at", "is_visible", "is_out_of_stock", "rejection_reason"]},
        "seller_shop_name": book.seller.shop_name if book.seller else "NXB",
        "category_name": book.category.name if book.category else "Chưa phân loại",
    }

@router.post("/books/{book_id}/approve")
def approve_book(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.UserRole.ADMIN.value]))
):
    book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Không tìm thấy sách")
    if book.status != models.BookStatus.PENDING.value:
        raise HTTPException(status_code=409, detail="Sách không còn ở trạng thái chờ duyệt")
    
    book.status = models.BookStatus.APPROVED.value
    book.is_visible = True
    book.rejection_reason = None
    book.rejected_at = None
    book.rejected_by = None
    db.commit()
    db.refresh(book)

    # Luồng 2 (Admin -> NXB): Gửi thông báo tới NXB
    try:
        notification_service.notify_seller_book_approved(db=db, book=book)
    except Exception as e:
        print(f"[NOTIFICATION ERROR] Không thể gửi thông báo phê duyệt tới NXB: {e}")

    return {"message": f"Đã duyệt cho phép cuốn '{book.title}' mở bán trên trang chủ!"}

@router.post("/books/{book_id}/reject")
def reject_book(
    book_id: int,
    reason: Optional[schemas.AdminReason] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.UserRole.ADMIN.value]))
):
    book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Không tìm thấy sách")
    if book.status != models.BookStatus.PENDING.value:
        raise HTTPException(status_code=409, detail="Sách không còn ở trạng thái chờ duyệt")
    
    book.status = models.BookStatus.REJECTED.value
    book.is_visible = False
    book.rejection_reason = reason.reason if reason else "Sản phẩm bị từ chối bởi Admin"
    book.rejected_at = datetime.utcnow()
    book.rejected_by = current_user.id
    db.commit()
    db.refresh(book)

    # Luồng 2 (Admin -> NXB): Gửi thông báo từ chối tới NXB
    rejection_reason_str = reason.reason if reason else None
    try:
        notification_service.notify_seller_book_rejected(db=db, book=book, reason=rejection_reason_str)
    except Exception as e:
        print(f"[NOTIFICATION ERROR] Không thể gửi thông báo từ chối tới NXB: {e}")

    return {"message": f"Đã từ chối cuốn '{book.title}'"}


@router.get("/disputes", response_model=List[schemas.DisputeOut])
def list_disputes(db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_role([models.UserRole.ADMIN.value]))):
    return db.query(models.Dispute).order_by(models.Dispute.created_at.desc()).all()


@router.get("/disputes/{dispute_id}", response_model=schemas.DisputeOut)
def get_dispute(dispute_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_role([models.UserRole.ADMIN.value]))):
    dispute = db.query(models.Dispute).filter(models.Dispute.id == dispute_id).first()
    if not dispute:
        raise HTTPException(status_code=404, detail="Không tìm thấy khiếu nại")
    return dispute


@router.post("/disputes/{dispute_id}/request-seller-response", response_model=schemas.DisputeOut)
def request_seller_response(dispute_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_role([models.UserRole.ADMIN.value]))):
    dispute = db.query(models.Dispute).filter(models.Dispute.id == dispute_id).first()
    if not dispute:
        raise HTTPException(status_code=404, detail="Không tìm thấy khiếu nại")
    dispute.status = "WAITING_SELLER"
    db.commit()
    db.refresh(dispute)
    return dispute


@router.post("/disputes/{dispute_id}/resolve", response_model=schemas.DisputeOut)
def resolve_dispute(dispute_id: int, decision: schemas.DisputeDecision, db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_role([models.UserRole.ADMIN.value]))):
    if decision.decision not in {"REFUND_BUYER", "RESOLVE_FOR_SELLER"}:
        raise HTTPException(status_code=400, detail="Quyết định xử lý không hợp lệ")
    dispute = db.query(models.Dispute).filter(models.Dispute.id == dispute_id).first()
    if not dispute:
        raise HTTPException(status_code=404, detail="Không tìm thấy khiếu nại")
    if dispute.status in {"RESOLVED", "REJECTED"}:
        raise HTTPException(status_code=409, detail="Khiếu nại đã được xử lý")
    dispute.status = "RESOLVED"
    dispute.admin_decision = decision.decision
    dispute.resolution_note = decision.note
    dispute.resolved_at = datetime.utcnow()
    dispute.resolved_by = current_user.id
    db.commit()
    db.refresh(dispute)
    return dispute


@router.post("/disputes/{dispute_id}/reject", response_model=schemas.DisputeOut)
def reject_dispute(dispute_id: int, payload: schemas.AdminReason, db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_role([models.UserRole.ADMIN.value]))):
    if not payload.reason.strip():
        raise HTTPException(status_code=422, detail="Vui lòng nhập lý do")
    dispute = db.query(models.Dispute).filter(models.Dispute.id == dispute_id).first()
    if not dispute:
        raise HTTPException(status_code=404, detail="Không tìm thấy khiếu nại")
    if dispute.status in {"RESOLVED", "REJECTED"}:
        raise HTTPException(status_code=409, detail="Khiếu nại đã được xử lý")
    dispute.status = "REJECTED"
    dispute.resolution_note = payload.reason
    dispute.resolved_at = datetime.utcnow()
    dispute.resolved_by = current_user.id
    db.commit()
    db.refresh(dispute)
    return dispute


@router.get("/payouts", response_model=List[schemas.WithdrawalRequestOut])
def list_payouts(db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_role([models.UserRole.ADMIN.value]))):
    return db.query(models.WithdrawalRequest).order_by(models.WithdrawalRequest.created_at.desc()).all()


@router.get("/payouts/{payout_id}", response_model=schemas.WithdrawalRequestOut)
def get_payout(payout_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_role([models.UserRole.ADMIN.value]))):
    payout = db.query(models.WithdrawalRequest).filter(models.WithdrawalRequest.id == payout_id).first()
    if not payout:
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu rút tiền")
    return payout


@router.post("/payouts/{payout_id}/approve", response_model=schemas.WithdrawalRequestOut)
def approve_payout(payout_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_role([models.UserRole.ADMIN.value]))):
    payout = db.query(models.WithdrawalRequest).filter(models.WithdrawalRequest.id == payout_id).first()
    if not payout:
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu rút tiền")
    if payout.status != "PENDING":
        raise HTTPException(status_code=409, detail="Yêu cầu không còn ở trạng thái chờ duyệt")
    seller = db.query(models.User).filter(models.User.id == payout.seller_id).first()
    if not seller or (seller.seller_balance or 0) < payout.amount:
        raise HTTPException(status_code=400, detail="Số dư seller không đủ")
    transaction = models.Transaction(transaction_code=f"TX-PAYOUT-{uuid.uuid4().hex[:10].upper()}", seller_id=payout.seller_id, payout_id=payout.id, transaction_type="PAYOUT", gross_amount=payout.amount, net_amount=payout.amount, status="PENDING", note="Đã duyệt nội bộ; chưa chuyển khoản ngân hàng")
    seller.seller_balance = (seller.seller_balance or 0) - payout.amount
    payout.status = "APPROVED"
    payout.processed_at = datetime.utcnow()
    payout.transaction_id = transaction.transaction_code
    db.add(transaction)
    db.commit()
    db.refresh(payout)
    return payout


@router.post("/payouts/{payout_id}/reject", response_model=schemas.WithdrawalRequestOut)
def reject_payout(payout_id: int, payload: schemas.AdminReason, db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_role([models.UserRole.ADMIN.value]))):
    if not payload.reason.strip():
        raise HTTPException(status_code=422, detail="Vui lòng nhập lý do")
    payout = db.query(models.WithdrawalRequest).filter(models.WithdrawalRequest.id == payout_id).first()
    if not payout:
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu rút tiền")
    if payout.status != "PENDING":
        raise HTTPException(status_code=409, detail="Yêu cầu không còn ở trạng thái chờ duyệt")
    payout.status = "REJECTED"
    payout.rejection_reason = payload.reason
    payout.processed_at = datetime.utcnow()
    db.commit()
    db.refresh(payout)
    return payout


@router.get("/documents/{document_id}", response_model=schemas.DocumentOut)
def get_document(document_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_role([models.UserRole.ADMIN.value]))):
    document = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu")
    return document


@router.get("/documents/{document_id}/preview")
def preview_document(document_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_role([models.UserRole.ADMIN.value]))):
    document = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu")
    if not os.path.isfile(document.storage_path):
        return {"available": False, "message": "Tài liệu chưa có trong storage backend", "document": document}
    return {"available": True, "file_url": f"/api/admin/documents/{document.id}/download", "document": document}


@router.get("/documents/{document_id}/download")
def download_document(document_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_role([models.UserRole.ADMIN.value]))):
    document = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not document or not os.path.isfile(document.storage_path):
        raise HTTPException(status_code=404, detail="Tệp tài liệu chưa có trong storage backend")
    return FileResponse(document.storage_path, media_type=document.mime_type, filename=document.file_name)

@router.get("/users")
def get_all_users(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.UserRole.ADMIN.value]))
):
    users = db.query(models.User).order_by(models.User.created_at.desc()).all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role,
            "status": u.status,
            "shop_name": u.shop_name,
            "phone": u.phone,
            "is_vip": u.is_vip,
            "created_at": u.created_at
        } for u in users
    ]

@router.post("/users/{user_id}/toggle-ban")
def toggle_ban_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.UserRole.ADMIN.value]))
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Không thể tự khóa tài khoản Admin chính mình")
        
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng")

    if user.status == models.UserStatus.BANNED.value:
        user.status = models.UserStatus.ACTIVE.value
        msg = f"Đã mở khóa tài khoản '{user.username}'"
    else:
        user.status = models.UserStatus.BANNED.value
        msg = f"Đã khóa tài khoản '{user.username}' do có dấu hiệu gian lận!"

    db.commit()
    return {"message": msg, "current_status": user.status}
