from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
import models, schemas, auth
import notification_service

router = APIRouter(prefix="/api/seller", tags=["Seller Portal"])

# =============================================================================
# MODULE 4 & DASHBOARD: Báo Cáo & Thống Kê Doanh Thu
# =============================================================================
@router.get("/dashboard")
def get_seller_dashboard(
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(auth.require_role([models.UserRole.SELLER.value, models.UserRole.ADMIN.value]))
):
    # Lấy các đơn hàng có sách của NXB này
    order_items = db.query(models.OrderItem).filter(models.OrderItem.seller_id == current_user.id).all()
    order_ids = list(set([item.order_id for item in order_items]))
    
    orders = db.query(models.Order).filter(models.Order.id.in_(order_ids)).all() if order_ids else []

    # Tổng doanh thu gộp và doanh thu thực nhận
    total_revenue_gross = 0.0
    for item in order_items:
        total_revenue_gross += (item.price * item.quantity)
    
    # Hoa hồng sàn khấu trừ 10%
    platform_commission = total_revenue_gross * 0.10
    net_earnings = total_revenue_gross - platform_commission

    total_books = db.query(models.Book).filter(models.Book.seller_id == current_user.id).count()
    approved_books = db.query(models.Book).filter(
        models.Book.seller_id == current_user.id,
        models.Book.status == models.BookStatus.APPROVED.value
    ).count()
    pending_books = db.query(models.Book).filter(
        models.Book.seller_id == current_user.id,
        models.Book.status == models.BookStatus.PENDING.value
    ).count()
    low_stock_books = db.query(models.Book).filter(
        models.Book.seller_id == current_user.id,
        models.Book.stock <= 5
    ).count()

    # Đơn hàng mới cần xử lý
    pending_orders_count = sum(1 for o in orders if o.status == models.OrderStatus.PENDING.value)
    packing_orders_count = sum(1 for o in orders if o.status == models.OrderStatus.PACKING.value)
    shipping_orders_count = sum(1 for o in orders if o.status == models.OrderStatus.SHIPPING.value)
    completed_orders_count = sum(1 for o in orders if o.status == models.OrderStatus.DELIVERED.value)
    return_orders_count = sum(1 for o in orders if getattr(o, 'return_status', 'NONE') in ['REQUESTED', 'APPROVED'])

    # Top 5 sách bán chạy nhất của Seller
    top_books_db = db.query(models.Book).filter(
        models.Book.seller_id == current_user.id
    ).order_by(models.Book.sold_count.desc()).limit(5).all()

    top_books = [
        {
            "id": b.id,
            "title": b.title,
            "cover_image": b.cover_image,
            "price": b.discount_price or b.price,
            "stock": b.stock,
            "sold_count": b.sold_count,
            "rating": b.rating
        } for b in top_books_db
    ]

    # Biểu đồ doanh thu 7 ngày gần nhất
    now = datetime.utcnow()
    chart_data = []
    for i in range(6, -1, -1):
        day_date = (now - timedelta(days=i)).date()
        day_label = day_date.strftime("%d/%m")
        # Doanh thu trong ngày đó
        day_orders = [
            o for o in orders 
            if o.created_at and (
                o.created_at.date() == day_date if hasattr(o.created_at, 'date') 
                else str(o.created_at)[:10] == str(day_date)
            )
        ]
        day_rev = 0.0
        for o in day_orders:
            for item in o.items:
                if item.seller_id == current_user.id:
                    day_rev += (item.price * item.quantity)
        chart_data.append({
            "date": day_label,
            "revenue": day_rev * 0.9, # Doanh thu thực nhận
            "orders": len(day_orders)
        })

    return {
        "shop_name": current_user.shop_name or current_user.full_name,
        "shop_logo": current_user.shop_logo,
        "total_revenue_gross": total_revenue_gross,
        "platform_commission_paid": platform_commission,
        "net_earnings": net_earnings,
        "seller_balance": (current_user.seller_balance or 0.0) + net_earnings,
        "total_orders": len(orders),
        "pending_orders_count": pending_orders_count,
        "packing_orders_count": packing_orders_count,
        "shipping_orders_count": shipping_orders_count,
        "completed_orders_count": completed_orders_count,
        "return_orders_count": return_orders_count,
        "total_books": total_books,
        "approved_books": approved_books,
        "pending_books": pending_books,
        "low_stock_books": low_stock_books,
        "top_books": top_books,
        "chart_data": chart_data
    }


# =============================================================================
# MODULE 1: Quản Lý Sản Phẩm & Tồn Kho (Product & Inventory)
# =============================================================================
@router.get("/books", response_model=List[schemas.BookOut])
def get_seller_books(
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(auth.require_role([models.UserRole.SELLER.value, models.UserRole.ADMIN.value]))
):
    books = db.query(models.Book).filter(
        models.Book.seller_id == current_user.id
    ).order_by(models.Book.created_at.desc()).all()
    
    results = []
    for b in books:
        results.append({
            "id": b.id,
            "seller_id": b.seller_id,
            "category_id": b.category_id,
            "title": b.title,
            "author": b.author,
            "publisher": b.publisher or current_user.shop_name,
            "price": b.price,
            "discount_price": b.discount_price,
            "stock": b.stock,
            "cover_image": b.cover_image,
            "description": b.description,
            "book_format": getattr(b, 'book_format', 'PAPER'),
            "cover_type": getattr(b, 'cover_type', 'SOFT'),
            "vip_eligible": getattr(b, 'vip_eligible', False),
            "isbn": getattr(b, 'isbn', None),
            "translator": getattr(b, 'translator', None),
            "page_count": getattr(b, 'page_count', None),
            "publication_year": getattr(b, 'publication_year', None),
            "language": getattr(b, 'language', 'Tiếng Việt'),
            "preview_file_url": getattr(b, 'preview_file_url', None),
            "sample_content": b.sample_content,
            "full_ebook_content": b.full_ebook_content,
            "status": b.status,
            "is_featured_ad": b.is_featured_ad,
            "sold_count": b.sold_count,
            "rating": b.rating,
            "created_at": b.created_at,
            "seller_shop_name": current_user.shop_name or current_user.full_name,
            "category_name": b.category.name if b.category else "Tổng hợp"
        })
    return results

@router.post("/books", response_model=schemas.BookOut)
def create_book(
    book_in: schemas.BookCreate, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(auth.require_role([models.UserRole.SELLER.value, models.UserRole.ADMIN.value]))
):
    new_book = models.Book(
        seller_id=current_user.id,
        category_id=book_in.category_id,
        title=book_in.title,
        author=book_in.author,
        publisher=book_in.publisher or current_user.shop_name or "NXB Kim Đồng",
        price=book_in.price,
        discount_price=book_in.discount_price,
        stock=book_in.stock,
        cover_image=book_in.cover_image or "https://images.unsplash.com/photo-1544947950-fa07a98d237f?auto=format&fit=crop&q=80&w=400",
        description=book_in.description,
        book_format=book_in.book_format or "PAPER",
        cover_type=book_in.cover_type or "SOFT",
        vip_eligible=book_in.vip_eligible or False,
        isbn=book_in.isbn,
        translator=book_in.translator,
        page_count=book_in.page_count,
        publication_year=book_in.publication_year or datetime.now().year,
        language=book_in.language or "Tiếng Việt",
        preview_file_url=book_in.preview_file_url,
        sample_content=book_in.sample_content,
        full_ebook_content=book_in.full_ebook_content,
        status=models.BookStatus.PENDING.value
    )
    db.add(new_book)
    db.commit()
    db.refresh(new_book)

    # Luồng 1 (NXB -> Admin): Gửi thông báo đến tất cả Admin
    try:
        notification_service.notify_admins_new_book(db=db, book=new_book, seller=current_user)
    except Exception as e:
        print(f"[NOTIFICATION ERROR] Không thể gửi thông báo tới Admin: {e}")

    return {
        "id": new_book.id,
        "seller_id": new_book.seller_id,
        "category_id": new_book.category_id,
        "title": new_book.title,
        "author": new_book.author,
        "publisher": new_book.publisher,
        "price": new_book.price,
        "discount_price": new_book.discount_price,
        "stock": new_book.stock,
        "cover_image": new_book.cover_image,
        "description": new_book.description,
        "book_format": new_book.book_format,
        "cover_type": new_book.cover_type,
        "vip_eligible": new_book.vip_eligible,
        "isbn": new_book.isbn,
        "translator": new_book.translator,
        "page_count": new_book.page_count,
        "publication_year": new_book.publication_year,
        "language": new_book.language,
        "preview_file_url": new_book.preview_file_url,
        "sample_content": new_book.sample_content,
        "full_ebook_content": new_book.full_ebook_content,
        "status": new_book.status,
        "is_featured_ad": new_book.is_featured_ad,
        "sold_count": new_book.sold_count,
        "rating": new_book.rating,
        "created_at": new_book.created_at,
        "seller_shop_name": current_user.shop_name,
        "category_name": ""
    }

@router.put("/books/{book_id}")
def update_book(
    book_id: int,
    book_in: schemas.BookUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.UserRole.SELLER.value, models.UserRole.ADMIN.value]))
):
    book = db.query(models.Book).filter(models.Book.id == book_id, models.Book.seller_id == current_user.id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Không tìm thấy cuốn sách này")
    
    update_data = book_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(book, field, value)
    
    db.commit()
    db.refresh(book)
    return {"message": "Cập nhật thông tin sách thành công", "book_id": book.id}

@router.delete("/books/{book_id}")
def delete_book(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.UserRole.SELLER.value, models.UserRole.ADMIN.value]))
):
    book = db.query(models.Book).filter(models.Book.id == book_id, models.Book.seller_id == current_user.id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Không tìm thấy cuốn sách này")
    
    db.delete(book)
    db.commit()
    return {"message": "Đã xóa sách khỏi kho thành công"}


# =============================================================================
# MODULE 2: Quản Lý Đơn Hàng & Vận Chuyển (Orders & Fulfillment)
# =============================================================================
@router.get("/orders")
def get_seller_orders(
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(auth.require_role([models.UserRole.SELLER.value, models.UserRole.ADMIN.value]))
):
    order_items = db.query(models.OrderItem).filter(models.OrderItem.seller_id == current_user.id).all()
    order_ids = list(set([item.order_id for item in order_items]))
    
    if not order_ids:
        return []

    query = db.query(models.Order).filter(models.Order.id.in_(order_ids))
    
    if status_filter and status_filter != "ALL":
        if status_filter == "RETURN":
            query = query.filter(models.Order.return_status.in_(["REQUESTED", "APPROVED"]))
        else:
            query = query.filter(models.Order.status == status_filter)

    orders = query.order_by(models.Order.created_at.desc()).all()
    
    results = []
    for o in orders:
        seller_items = [i for i in o.items if i.seller_id == current_user.id]
        seller_total = sum(i.price * i.quantity for i in seller_items)
        seller_fee = seller_total * 0.10
        seller_net = seller_total - seller_fee

        results.append({
            "id": o.id,
            "order_code": o.order_code,
            "created_at": o.created_at,
            "status": o.status,
            "tracking_step": o.tracking_step,
            "shipping_name": o.shipping_name,
            "shipping_phone": o.shipping_phone,
            "shipping_address": o.shipping_address,
            "shipping_carrier": o.shipping_carrier or "Giao Hàng Nhanh (GHN Express)",
            "tracking_number": getattr(o, 'tracking_number', None),
            "return_status": getattr(o, 'return_status', 'NONE'),
            "return_reason": getattr(o, 'return_reason', None),
            "payment_method": o.payment_method,
            "payment_status": o.payment_status,
            "items": [
                {
                    "id": item.id,
                    "book_id": item.book_id,
                    "book_title": item.book_title,
                    "book_cover": item.book_cover,
                    "quantity": item.quantity,
                    "price": item.price
                } for item in seller_items
            ],
            "seller_total": seller_total,
            "seller_fee": seller_fee,
            "seller_net": seller_net
        })
    return results

@router.post("/orders/{order_id}/update-status")
def update_order_status(
    order_id: int, 
    new_status: Optional[str] = None,
    carrier: Optional[str] = None,
    tracking_code: Optional[str] = None,
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(auth.require_role([models.UserRole.SELLER.value, models.UserRole.ADMIN.value]))
):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng")
    if current_user.role == models.UserRole.SELLER.value and not any(item.seller_id == current_user.id for item in order.items):
        raise HTTPException(status_code=403, detail="Bạn không có quyền cập nhật đơn hàng này")

    if new_status:
        if new_status == models.OrderStatus.PACKING.value:
            order.status = models.OrderStatus.PACKING.value
            order.tracking_step = 2 # Xác nhận đóng gói
        elif new_status == models.OrderStatus.SHIPPING.value:
            order.status = models.OrderStatus.SHIPPING.value
            order.tracking_step = 3 # Đang giao
        elif new_status == models.OrderStatus.DELIVERED.value:
            order.status = models.OrderStatus.DELIVERED.value
            order.tracking_step = 4 # Đã giao thành công
        elif new_status == models.OrderStatus.CANCELLED.value:
            order.status = models.OrderStatus.CANCELLED.value
        else:
            order.status = new_status

    if carrier:
        order.shipping_carrier = carrier
    if tracking_code:
        order.tracking_number = tracking_code
    elif not getattr(order, 'tracking_number', None):
        order.tracking_number = f"VN-{order.id:06d}-GHN"

    db.commit()
    db.refresh(order)
    return {
        "message": f"Cập nhật đơn hàng thành công: {order.status}",
        "status": order.status,
        "tracking_step": order.tracking_step,
        "tracking_number": order.tracking_number,
        "shipping_carrier": order.shipping_carrier
    }

@router.post("/orders/{order_id}/handle-return")
def handle_order_return(
    order_id: int,
    action: str, # APPROVE or REJECT
    note: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.UserRole.SELLER.value, models.UserRole.ADMIN.value]))
):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng")
    if current_user.role == models.UserRole.SELLER.value and not any(item.seller_id == current_user.id for item in order.items):
        raise HTTPException(status_code=403, detail="Bạn không có quyền xử lý đơn hàng này")
    
    if action == "APPROVE":
        order.return_status = "APPROVED"
        order.status = "RETURNED"
        msg = "Đã phê duyệt yêu cầu đổi trả / hoàn tiền thành công."
    else:
        order.return_status = "REJECTED"
        msg = "Đã từ chối yêu cầu đổi trả."
        
    db.commit()
    return {"message": msg, "return_status": order.return_status}


# =============================================================================
# MODULE 3: Quản Lý Khuyến Mãi & Marketing (Vouchers & Ads)
# =============================================================================
@router.get("/vouchers", response_model=List[schemas.ShopVoucherOut])
def get_seller_vouchers(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.UserRole.SELLER.value, models.UserRole.ADMIN.value]))
):
    vouchers = db.query(models.Voucher).filter(models.Voucher.seller_id == current_user.id).order_by(models.Voucher.id.desc()).all()
    return vouchers

@router.post("/vouchers", response_model=schemas.ShopVoucherOut)
def create_seller_voucher(
    voucher_in: schemas.ShopVoucherCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.UserRole.SELLER.value, models.UserRole.ADMIN.value]))
):
    # Kiểm tra trùng mã code
    existing = db.query(models.Voucher).filter(models.Voucher.code == voucher_in.code.upper().strip()).first()
    if existing:
        raise HTTPException(status_code=400, detail="Mã Voucher này đã tồn tại trên hệ thống!")

    expires_at = voucher_in.expires_at or (datetime.utcnow() + timedelta(days=30))

    new_voucher = models.Voucher(
        seller_id=current_user.id,
        code=voucher_in.code.upper().strip(),
        name=voucher_in.name,
        discount_type=voucher_in.discount_type,
        discount_value=voucher_in.discount_value,
        max_discount=voucher_in.max_discount,
        min_order_amount=voucher_in.min_order_amount,
        usage_limit=voucher_in.usage_limit or 100,
        used_count=0,
        starts_at=datetime.utcnow(),
        expires_at=expires_at,
        is_active=True
    )
    db.add(new_voucher)
    db.commit()
    db.refresh(new_voucher)
    return new_voucher

@router.delete("/vouchers/{voucher_id}")
def delete_seller_voucher(
    voucher_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.UserRole.SELLER.value, models.UserRole.ADMIN.value]))
):
    voucher = db.query(models.Voucher).filter(models.Voucher.id == voucher_id, models.Voucher.seller_id == current_user.id).first()
    if not voucher:
        raise HTTPException(status_code=404, detail="Không tìm thấy voucher này")
    db.delete(voucher)
    db.commit()
    return {"message": "Đã xóa voucher thành công"}

@router.post("/ads/purchase")
def purchase_ad(
    ad_in: schemas.AdPurchaseRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.UserRole.SELLER.value, models.UserRole.ADMIN.value]))
):
    book = db.query(models.Book).filter(models.Book.id == ad_in.book_id, models.Book.seller_id == current_user.id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Không tìm thấy sách của bạn")

    now = datetime.utcnow()
    end_date = now + timedelta(days=ad_in.duration_days)

    book.is_featured_ad = True
    book.ad_expires_at = end_date

    campaign = models.AdCampaign(
        seller_id=current_user.id,
        book_id=book.id,
        fee_paid=ad_in.fee_paid,
        duration_days=ad_in.duration_days,
        start_date=now,
        end_date=end_date,
        status="ACTIVE"
    )
    db.add(campaign)
    db.commit()

    return {
        "message": f"Kích hoạt quảng cáo thành công cho cuốn '{book.title}' trong {ad_in.duration_days} ngày!",
        "fee_paid": ad_in.fee_paid,
        "expires_at": end_date
    }


# =============================================================================
# MODULE 4: Tài Chính & Rút Tiền (Withdrawals & Settlement)
# =============================================================================
@router.get("/withdrawals", response_model=List[schemas.WithdrawalRequestOut])
def get_seller_withdrawals(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.UserRole.SELLER.value, models.UserRole.ADMIN.value]))
):
    withdrawals = db.query(models.WithdrawalRequest).filter(
        models.WithdrawalRequest.seller_id == current_user.id
    ).order_by(models.WithdrawalRequest.created_at.desc()).all()
    return withdrawals

@router.post("/withdrawals", response_model=schemas.WithdrawalRequestOut)
def create_withdrawal(
    req_in: schemas.WithdrawalRequestCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.UserRole.SELLER.value, models.UserRole.ADMIN.value]))
):
    if req_in.amount < 50000:
        raise HTTPException(status_code=400, detail="Số tiền rút tối thiểu là 50.000 đ")

    # Tính tổng số dư thực
    order_items = db.query(models.OrderItem).filter(models.OrderItem.seller_id == current_user.id).all()
    total_rev = sum(item.price * item.quantity for item in order_items)
    net_earnings = total_rev * 0.90
    available_balance = (current_user.seller_balance or 0.0) + net_earnings

    if req_in.amount > available_balance:
        raise HTTPException(status_code=400, detail="Số dư khả dụng không đủ để thực hiện yêu cầu rút tiền!")

    # Tạo yêu cầu rút tiền
    withdrawal = models.WithdrawalRequest(
        seller_id=current_user.id,
        amount=req_in.amount,
        bank_name=req_in.bank_name,
        bank_account_number=req_in.bank_account_number,
        bank_account_holder=req_in.bank_account_holder,
        status="PENDING",
        note=req_in.note or "Yêu cầu rút tiền định kỳ",
        created_at=datetime.utcnow()
    )
    db.add(withdrawal)
    db.commit()
    db.refresh(withdrawal)
    return withdrawal


# =============================================================================
# MODULE 5: Hồ Sơ Gian Hàng & Phân Quyền (Store Profile & Settings)
# =============================================================================
@router.get("/profile")
def get_seller_profile(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.UserRole.SELLER.value, models.UserRole.ADMIN.value]))
):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "email": current_user.email,
        "phone": current_user.phone,
        "shop_name": current_user.shop_name or current_user.full_name,
        "shop_description": current_user.shop_description,
        "business_license": current_user.business_license,
        "tax_code": getattr(current_user, 'tax_code', None) or "0101234567-001",
        "bank_name": getattr(current_user, 'bank_name', None) or "Vietcombank",
        "bank_account_number": getattr(current_user, 'bank_account_number', None) or "0071001234567",
        "bank_account_holder": getattr(current_user, 'bank_account_holder', None) or current_user.shop_name or current_user.full_name,
        "warehouse_address": getattr(current_user, 'warehouse_address', None) or current_user.address or "Kho 1: 55 Quang Trung, P. Nguyễn Du, Q. Hai Bà Trưng, Hà Nội",
        "shop_logo": getattr(current_user, 'shop_logo', None) or "https://images.unsplash.com/photo-1544947950-fa07a98d237f?auto=format&fit=crop&q=80&w=200",
        "shop_banner": getattr(current_user, 'shop_banner', None) or "https://images.unsplash.com/photo-1507842229451-7f01be637b52?auto=format&fit=crop&q=80&w=1200",
        "seller_balance": current_user.seller_balance or 0.0
    }

@router.put("/profile")
def update_seller_profile(
    profile_in: schemas.SellerProfileUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.UserRole.SELLER.value, models.UserRole.ADMIN.value]))
):
    update_data = profile_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(current_user, field):
            setattr(current_user, field, value)
    
    db.commit()
    db.refresh(current_user)
    return {"message": "Cập nhật hồ sơ gian hàng thành công!"}

@router.get("/staff", response_model=List[schemas.SellerStaffOut])
def get_seller_staff(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.UserRole.SELLER.value, models.UserRole.ADMIN.value]))
):
    staff_list = db.query(models.SellerStaff).filter(models.SellerStaff.seller_id == current_user.id).all()
    # Nếu chưa có nhân viên mẫu, khởi tạo sẵn 2 nhân viên mẫu
    if not staff_list:
        sample_staff = [
            models.SellerStaff(
                seller_id=current_user.id,
                staff_name="Nguyễn Văn Kho",
                staff_email="kho.kimdong@bookhub.vn",
                staff_phone="0987111222",
                role="WAREHOUSE",
                status="ACTIVE"
            ),
            models.SellerStaff(
                seller_id=current_user.id,
                staff_name="Trần Thị Marketing",
                staff_email="mkt.kimdong@bookhub.vn",
                staff_phone="0987333444",
                role="MARKETING",
                status="ACTIVE"
            )
        ]
        db.add_all(sample_staff)
        db.commit()
        staff_list = db.query(models.SellerStaff).filter(models.SellerStaff.seller_id == current_user.id).all()

    return staff_list

@router.post("/staff", response_model=schemas.SellerStaffOut)
def create_seller_staff(
    staff_in: schemas.SellerStaffCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.UserRole.SELLER.value, models.UserRole.ADMIN.value]))
):
    new_staff = models.SellerStaff(
        seller_id=current_user.id,
        staff_name=staff_in.staff_name,
        staff_email=staff_in.staff_email,
        staff_phone=staff_in.staff_phone,
        role=staff_in.role,
        status="ACTIVE"
    )
    db.add(new_staff)
    db.commit()
    db.refresh(new_staff)
    return new_staff

@router.delete("/staff/{staff_id}")
def delete_seller_staff(
    staff_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.UserRole.SELLER.value, models.UserRole.ADMIN.value]))
):
    staff = db.query(models.SellerStaff).filter(models.SellerStaff.id == staff_id, models.SellerStaff.seller_id == current_user.id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhân viên này")
    db.delete(staff)
    db.commit()
    return {"message": "Đã xóa nhân viên thành công"}

# =============================================================================
# EXTENDED SELLER FEATURES: Quick Stock, Bulk Actions, Monthly Stats
# =============================================================================

@router.put("/books/{book_id}/quick-stock")
def update_book_quick_stock(
    book_id: int,
    stock_in: schemas.SellerQuickStockUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.UserRole.SELLER.value, models.UserRole.ADMIN.value]))
):
    book = db.query(models.Book).filter(models.Book.id == book_id, models.Book.seller_id == current_user.id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Không tìm thấy sách")
    if stock_in.stock < 0:
        raise HTTPException(status_code=400, detail="Số lượng tồn kho không hợp lệ")
    book.stock = stock_in.stock
    db.commit()
    db.refresh(book)
    return {"message": "Cập nhật tồn kho thành công", "id": book.id, "stock": book.stock}

@router.post("/orders/bulk-confirm")
def bulk_confirm_orders(
    bulk_in: schemas.SellerBulkOrderConfirm,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.UserRole.SELLER.value, models.UserRole.ADMIN.value]))
):
    if not bulk_in.order_ids:
        raise HTTPException(status_code=400, detail="Danh sách mã đơn hàng rỗng")
    
    order_items = db.query(models.OrderItem).filter(
        models.OrderItem.order_id.in_(bulk_in.order_ids),
        models.OrderItem.seller_id == current_user.id
    ).all()
    valid_order_ids = list(set([item.order_id for item in order_items]))
    
    orders = db.query(models.Order).filter(
        models.Order.id.in_(valid_order_ids),
        models.Order.status == models.OrderStatus.PENDING.value
    ).all()
    
    confirmed_count = 0
    for order in orders:
        order.status = models.OrderStatus.PACKING.value
        if not order.tracking_carrier:
            order.tracking_carrier = "Giao Hàng Nhanh (GHN Express)"
        if not order.tracking_number:
            order.tracking_number = f"GHN{order.id:06d}VN"
        confirmed_count += 1
        
    db.commit()
    return {"message": f"Đã xác nhận và chuyển sang đóng gói {confirmed_count} đơn hàng", "confirmed_count": confirmed_count}

@router.get("/stats/monthly")
def get_monthly_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.UserRole.SELLER.value, models.UserRole.ADMIN.value]))
):
    now = datetime.utcnow()
    first_day_this_month = datetime(now.year, now.month, 1)
    
    order_items_this_month = db.query(models.OrderItem).join(models.Order).filter(
        models.OrderItem.seller_id == current_user.id,
        models.Order.created_at >= first_day_this_month
    ).all()
    
    month_revenue = sum(item.price * item.quantity for item in order_items_this_month)
    month_orders_count = len(set(item.order_id for item in order_items_this_month))
    new_books_count = db.query(models.Book).filter(
        models.Book.seller_id == current_user.id,
        models.Book.created_at >= first_day_this_month
    ).count() if hasattr(models.Book, 'created_at') else 0
    
    return {
        "month": f"Tháng {now.month}/{now.year}",
        "gross_revenue": month_revenue,
        "net_revenue": month_revenue * 0.9,
        "orders_count": month_orders_count,
        "new_books_count": new_books_count
    }
