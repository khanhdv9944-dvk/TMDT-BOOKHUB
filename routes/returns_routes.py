from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

import auth
import models
import schemas
from database import get_db

buyer_router = APIRouter(prefix="/api", tags=["Returns"])
seller_router = APIRouter(prefix="/api/seller", tags=["Seller Returns"])
admin_router = APIRouter(prefix="/api/admin", tags=["Admin Returns"])


def _serialize_return_request(request: models.ReturnRequest) -> dict:
    return {
        "id": request.id,
        "order_id": request.order_id,
        "user_id": request.user_id,
        "status": request.status,
        "reason": request.reason,
        "description": request.description,
        "refund_method": request.refund_method,
        "refund_amount": request.refund_amount or 0.0,
        "rejection_reason": request.rejection_reason,
        "admin_note": request.admin_note,
        "created_at": request.created_at,
        "updated_at": request.updated_at,
        "approved_at": request.approved_at,
        "shipped_at": request.shipped_at,
        "received_at": request.received_at,
        "refunded_at": request.refunded_at,
        "cancelled_at": request.cancelled_at,
        "items": [
            {
                "id": item.id,
                "order_item_id": item.order_item_id,
                "product_id": item.product_id,
                "product_name": item.product_name or (item.product.title if item.product else None),
                "quantity": item.quantity,
                "unit_price": item.unit_price,
            }
            for item in (request.items or [])
        ],
    }


@buyer_router.get("/returns")
def list_my_return_requests(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    requests = (
        db.query(models.ReturnRequest)
        .filter(models.ReturnRequest.user_id == current_user.id)
        .order_by(models.ReturnRequest.created_at.desc())
        .all()
    )
    return [_serialize_return_request(req) for req in requests]


@buyer_router.post("/returns")
def create_return_request(
    payload: schemas.ReturnRequestCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    order = (
        db.query(models.Order)
        .filter(models.Order.id == payload.order_id, models.Order.buyer_id == current_user.id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng để yêu cầu hoàn trả")

    if not payload.items:
        raise HTTPException(status_code=400, detail="Vui lòng chọn ít nhất 1 sản phẩm để hoàn trả")

    refund_total = 0.0
    return_request = models.ReturnRequest(
        order_id=payload.order_id,
        user_id=current_user.id,
        status=models.ReturnRequestStatus.PENDING.value,
        reason=payload.reason,
        description=payload.description,
        refund_method=payload.refund_method or "BANK_TRANSFER",
        refund_amount=0.0,
    )
    db.add(return_request)
    db.flush()

    for item in payload.items:
        order_item = (
            db.query(models.OrderItem)
            .filter(models.OrderItem.id == item.order_item_id, models.OrderItem.order_id == payload.order_id)
            .first()
        )
        if not order_item:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy sản phẩm #{item.order_item_id} trong đơn hàng")

        product = db.query(models.Book).filter(models.Book.id == item.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy sản phẩm #{item.product_id}")

        if item.quantity <= 0 or item.quantity > order_item.quantity:
            raise HTTPException(status_code=400, detail=f"Số lượng hoàn trả không hợp lệ cho sản phẩm #{order_item.id}")

        unit_price = float(order_item.price or 0)
        refund_total += unit_price * item.quantity

        db.add(
            models.ReturnRequestItem(
                return_request_id=return_request.id,
                order_item_id=item.order_item_id,
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=unit_price,
                product_name=order_item.book_title or product.title,
            )
        )

    return_request.refund_amount = refund_total
    order.return_status = "REQUESTED"
    order.return_reason = payload.reason
    db.commit()
    db.refresh(return_request)
    return _serialize_return_request(return_request)


@seller_router.get("/returns")
def list_seller_return_requests(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.UserRole.SELLER.value, models.UserRole.ADMIN.value])),
):
    requests = (
        db.query(models.ReturnRequest)
        .join(models.ReturnRequestItem, models.ReturnRequestItem.return_request_id == models.ReturnRequest.id)
        .join(models.OrderItem, models.OrderItem.id == models.ReturnRequestItem.order_item_id)
        .filter(models.OrderItem.seller_id == current_user.id)
        .distinct()
        .order_by(models.ReturnRequest.created_at.desc())
        .all()
    )
    return [_serialize_return_request(req) for req in requests]


@seller_router.patch("/returns/{return_id}/approve")
def approve_seller_return_request(
    return_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.UserRole.SELLER.value, models.UserRole.ADMIN.value])),
):
    request = db.query(models.ReturnRequest).filter(models.ReturnRequest.id == return_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu hoàn trả")
    request.status = models.ReturnRequestStatus.APPROVED.value
    request.approved_at = datetime.utcnow()
    request.admin_note = (request.admin_note or "") + " | Seller approved"
    db.commit()
    db.refresh(request)
    return _serialize_return_request(request)


@seller_router.patch("/returns/{return_id}/reject")
def reject_seller_return_request(
    return_id: int,
    payload: dict | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.UserRole.SELLER.value, models.UserRole.ADMIN.value])),
):
    request = db.query(models.ReturnRequest).filter(models.ReturnRequest.id == return_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu hoàn trả")
    data = payload or {}
    rejection_reason = data.get("rejection_reason") or "Yêu cầu hoàn trả bị từ chối bởi seller"
    request.status = models.ReturnRequestStatus.REJECTED.value
    request.rejection_reason = rejection_reason
    request.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(request)
    return _serialize_return_request(request)


@admin_router.get("/returns")
def list_admin_return_requests(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.UserRole.ADMIN.value])),
):
    requests = db.query(models.ReturnRequest).order_by(models.ReturnRequest.created_at.desc()).all()
    return [_serialize_return_request(req) for req in requests]


@admin_router.patch("/returns/{return_id}/approve")
def admin_approve_return_request(
    return_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.UserRole.ADMIN.value])),
):
    request = db.query(models.ReturnRequest).filter(models.ReturnRequest.id == return_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu hoàn trả")
    request.status = models.ReturnRequestStatus.APPROVED.value
    request.approved_at = datetime.utcnow()
    request.admin_note = request.admin_note or "Admin đã duyệt"
    db.commit()
    db.refresh(request)
    return _serialize_return_request(request)


@admin_router.patch("/returns/{return_id}/reject")
def admin_reject_return_request(
    return_id: int,
    payload: dict | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.UserRole.ADMIN.value])),
):
    request = db.query(models.ReturnRequest).filter(models.ReturnRequest.id == return_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu hoàn trả")
    data = payload or {}
    request.status = models.ReturnRequestStatus.REJECTED.value
    request.rejection_reason = data.get("rejection_reason") or "Không đạt tiêu chí hoàn trả"
    request.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(request)
    return _serialize_return_request(request)


@admin_router.patch("/returns/{return_id}/received")
def admin_mark_return_received(
    return_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.UserRole.ADMIN.value])),
):
    request = db.query(models.ReturnRequest).filter(models.ReturnRequest.id == return_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu hoàn trả")
    request.status = models.ReturnRequestStatus.RECEIVED.value
    request.received_at = datetime.utcnow()
    db.commit()
    db.refresh(request)
    return _serialize_return_request(request)


@admin_router.patch("/returns/{return_id}/refund")
def admin_refund_return_request(
    return_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.UserRole.ADMIN.value])),
):
    request = db.query(models.ReturnRequest).filter(models.ReturnRequest.id == return_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu hoàn trả")
    request.status = models.ReturnRequestStatus.REFUNDED.value
    request.refunded_at = datetime.utcnow()
    request.updated_at = datetime.utcnow()
    order = db.query(models.Order).filter(models.Order.id == request.order_id).first()
    if order:
        order.return_status = models.ReturnRequestStatus.REFUNDED.value
        order.payment_status = models.PaymentStatus.CANCELLED.value
    db.commit()
    db.refresh(request)
    return _serialize_return_request(request)
