from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import models, auth
from database import get_db

router = APIRouter(prefix="/api", tags=["Return Requests"])


def _serialize_return_request(db: Session, req: models.ReturnRequest) -> dict:
    order = req.order
    user = req.user
    items = []
    for item in (req.items or []):
        product = item.product
        items.append({
            "id": item.id,
            "order_item_id": item.order_item_id,
            "product_id": item.product_id,
            "quantity": item.quantity,
            "unit_price": item.unit_price,
            "product_name": item.product_name or (product.title if product else None),
            "product_cover": product.cover_image if product else None,
        })

    return {
        "id": req.id,
        "order_id": req.order_id,
        "order_code": order.order_code if order else f"ORDER-{req.order_id}",
        "user_id": req.user_id,
        "customer_name": user.full_name or user.username if user else "Khách hàng",
        "customer_email": user.email if user else "",
        "status": req.status,
        "reason": req.reason,
        "description": req.description,
        "refund_method": req.refund_method,
        "refund_amount": req.refund_amount,
        "rejection_reason": req.rejection_reason,
        "admin_note": req.admin_note,
        "created_at": req.created_at,
        "updated_at": req.updated_at,
        "approved_at": req.approved_at,
        "shipped_at": req.shipped_at,
        "received_at": req.received_at,
        "refunded_at": req.refunded_at,
        "cancelled_at": req.cancelled_at,
        "items": items,
    }


# =============================================================================
# BUYER ENDPOINTS
# =============================================================================

@router.post("/returns", response_model=dict)
def create_return_request(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    order_id = payload.get("order_id")
    if not order_id:
        raise HTTPException(status_code=400, detail="Thiếu order_id")

    order = db.query(models.Order).filter(models.Order.id == int(order_id)).first()
    if not order:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng")
    if order.buyer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Bạn không có quyền gửi yêu cầu cho đơn hàng này")

    items_payload = payload.get("items") or []
    if not items_payload:
        raise HTTPException(status_code=400, detail="Vui lòng chọn ít nhất một sản phẩm để trả")

    reason = payload.get("reason") or "OTHER"
    description = payload.get("description") or ""
    refund_method = payload.get("refund_method") or "BANK_TRANSFER"

    # Kiểm tra xem đã có yêu cầu trả hàng đang xử lý cho đơn hàng này chưa
    existing = db.query(models.ReturnRequest).filter(
        models.ReturnRequest.order_id == order.id,
        models.ReturnRequest.status.notin_([models.ReturnRequestStatus.REJECTED.value, models.ReturnRequestStatus.CANCELLED.value])
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Đơn hàng này đã có yêu cầu trả hàng đang được xử lý")

    total_refund = 0.0
    items_to_create = []

    for item_data in items_payload:
        order_item_id = item_data.get("order_item_id")
        product_id = item_data.get("product_id")
        quantity = int(item_data.get("quantity") or 1)

        order_item = db.query(models.OrderItem).filter(
            models.OrderItem.id == order_item_id,
            models.OrderItem.order_id == order.id
        ).first()

        if not order_item:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy sản phẩm trong đơn hàng (ID: {order_item_id})")

        unit_price = order_item.price or 0.0
        product_name = order_item.book_title or (order_item.book.title if order_item.book else "Sản phẩm")
        total_refund += unit_price * quantity

        req_item = models.ReturnRequestItem(
            order_item_id=order_item.id,
            product_id=product_id or order_item.book_id,
            quantity=quantity,
            unit_price=unit_price,
            product_name=product_name
        )
        items_to_create.append(req_item)

    return_req = models.ReturnRequest(
        order_id=order.id,
        user_id=current_user.id,
        status=models.ReturnRequestStatus.PENDING.value,
        reason=reason,
        description=description,
        refund_method=refund_method,
        refund_amount=total_refund,
        created_at=datetime.utcnow(),
    )
    db.add(return_req)
    db.flush()

    for item in items_to_create:
        item.return_request_id = return_req.id
        db.add(item)

    order.return_status = "REQUESTED"
    order.return_reason = reason

    db.commit()
    db.refresh(return_req)
    return _serialize_return_request(db, return_req)


@router.get("/returns", response_model=List[dict])
@router.get("/returns/my", response_model=List[dict])
def get_my_return_requests(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    requests = db.query(models.ReturnRequest).filter(
        models.ReturnRequest.user_id == current_user.id
    ).order_by(models.ReturnRequest.created_at.desc()).all()
    return [_serialize_return_request(db, req) for req in requests]


# =============================================================================
# SELLER ENDPOINTS
# =============================================================================

@router.get("/seller/returns", response_model=List[dict])
def get_seller_return_requests(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.UserRole.SELLER.value, models.UserRole.ADMIN.value])),
):
    if current_user.role == models.UserRole.ADMIN.value:
        requests = db.query(models.ReturnRequest).order_by(models.ReturnRequest.created_at.desc()).all()
    else:
        # Lấy các yêu cầu trả hàng có chứa sản phẩm của gian hàng này
        requests = db.query(models.ReturnRequest).join(models.ReturnRequestItem).join(models.OrderItem).filter(
            models.OrderItem.seller_id == current_user.id
        ).order_by(models.ReturnRequest.created_at.desc()).distinct().all()

    return [_serialize_return_request(db, req) for req in requests]


@router.post("/seller/returns/{return_id}/approve", response_model=dict)
def seller_approve_return(
    return_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.UserRole.SELLER.value, models.UserRole.ADMIN.value])),
):
    req = db.query(models.ReturnRequest).filter(models.ReturnRequest.id == return_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu trả hàng")

    req.status = models.ReturnRequestStatus.APPROVED.value
    req.approved_at = datetime.utcnow()
    req.updated_at = datetime.utcnow()
    if req.order:
        req.order.return_status = "APPROVED"

    db.commit()
    db.refresh(req)
    return _serialize_return_request(db, req)


@router.post("/seller/returns/{return_id}/reject", response_model=dict)
def seller_reject_return(
    return_id: int,
    payload: Optional[dict] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.UserRole.SELLER.value, models.UserRole.ADMIN.value])),
):
    req = db.query(models.ReturnRequest).filter(models.ReturnRequest.id == return_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu trả hàng")

    reason = (payload or {}).get("rejection_reason") or "Không đạt tiêu chí hoàn trả"
    req.status = models.ReturnRequestStatus.REJECTED.value
    req.rejection_reason = reason
    req.updated_at = datetime.utcnow()
    if req.order:
        req.order.return_status = "REJECTED"

    db.commit()
    db.refresh(req)
    return _serialize_return_request(db, req)


# =============================================================================
# ADMIN ENDPOINTS
# =============================================================================

@router.get("/admin/returns", response_model=List[dict])
def get_admin_return_requests(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.UserRole.ADMIN.value])),
):
    requests = db.query(models.ReturnRequest).order_by(models.ReturnRequest.created_at.desc()).all()
    return [_serialize_return_request(db, req) for req in requests]


@router.post("/admin/returns/{return_id}/approve", response_model=dict)
def admin_approve_return(
    return_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.UserRole.ADMIN.value])),
):
    req = db.query(models.ReturnRequest).filter(models.ReturnRequest.id == return_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu trả hàng")

    req.status = models.ReturnRequestStatus.APPROVED.value
    req.approved_at = datetime.utcnow()
    req.updated_at = datetime.utcnow()
    if req.order:
        req.order.return_status = "APPROVED"

    db.commit()
    db.refresh(req)
    return _serialize_return_request(db, req)


@router.post("/admin/returns/{return_id}/reject", response_model=dict)
def admin_reject_return(
    return_id: int,
    payload: Optional[dict] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.UserRole.ADMIN.value])),
):
    req = db.query(models.ReturnRequest).filter(models.ReturnRequest.id == return_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu trả hàng")

    reason = (payload or {}).get("rejection_reason") or "Từ chối bởi Admin"
    req.status = models.ReturnRequestStatus.REJECTED.value
    req.rejection_reason = reason
    req.updated_at = datetime.utcnow()
    if req.order:
        req.order.return_status = "REJECTED"

    db.commit()
    db.refresh(req)
    return _serialize_return_request(db, req)


@router.post("/admin/returns/{return_id}/received", response_model=dict)
def admin_received_return(
    return_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.UserRole.ADMIN.value])),
):
    req = db.query(models.ReturnRequest).filter(models.ReturnRequest.id == return_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu trả hàng")

    req.status = models.ReturnRequestStatus.RECEIVED.value
    req.received_at = datetime.utcnow()
    req.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(req)
    return _serialize_return_request(db, req)


@router.post("/admin/returns/{return_id}/refund", response_model=dict)
def admin_refund_return(
    return_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.UserRole.ADMIN.value])),
):
    req = db.query(models.ReturnRequest).filter(models.ReturnRequest.id == return_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu trả hàng")

    req.status = models.ReturnRequestStatus.REFUNDED.value
    req.refunded_at = datetime.utcnow()
    req.updated_at = datetime.utcnow()
    if req.order:
        req.order.return_status = "REFUNDED"

    db.commit()
    db.refresh(req)
    return _serialize_return_request(db, req)
