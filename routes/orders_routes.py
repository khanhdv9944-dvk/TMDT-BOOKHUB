import uuid
import json
from urllib.request import urlopen
from datetime import datetime, timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
import models, schemas, auth
import notification_service
from financial import COMMISSION_RATE, COMMISSION_RATE_PERCENT, calculate_commission

router = APIRouter(prefix="/api/orders", tags=["Orders"])

PLATFORM_COMMISSION_RATE = COMMISSION_RATE_PERCENT

SHIPPING_METHODS = {
    "STANDARD": {"name": "Giao tiết kiệm", "description": "Dự kiến nhận sau 2-4 ngày", "fee": 25000.0, "delivery_estimate": "12/09 - 14/09"},
    "EXPRESS": {"name": "Giao nhanh", "description": "Ưu tiên xử lý đơn hàng", "fee": 40000.0, "delivery_estimate": "11/09 - 12/09"},
    "SAME_DAY": {"name": "Giao hỏa tốc", "description": "Trong khu vực hỗ trợ", "fee": 60000.0, "delivery_estimate": "10/09"},
}

PAYMENT_METHODS = {"COD", "VIETQR", "MOMO", "ZALOPAY", "SHOPEEPAY", "CARD"}
LOCATION_API_URL = "https://provinces.open-api.vn/api/?depth=3"
LOCATION_CACHE = None

FALLBACK_LOCATIONS = [
    {"code": "79", "name": "Thành phố Hồ Chí Minh", "districts": [{"code": "760", "name": "Quận 1", "wards": [{"code": "26734", "name": "Phường Bến Nghé"}, {"code": "26737", "name": "Phường Đa Kao"}]}, {"code": "770", "name": "Quận 3", "wards": [{"code": "26743", "name": "Phường Võ Thị Sáu"}, {"code": "26752", "name": "Phường 7"}]}]},
    {"code": "01", "name": "Thành phố Hà Nội", "districts": [{"code": "002", "name": "Quận Hoàn Kiếm", "wards": [{"code": "00058", "name": "Phường Hàng Bạc"}, {"code": "00061", "name": "Phường Tràng Tiền"}]}, {"code": "005", "name": "Quận Cầu Giấy", "wards": [{"code": "00175", "name": "Phường Dịch Vọng"}, {"code": "00178", "name": "Phường Yên Hòa"}]}]},
]

def _get_locations():
    global LOCATION_CACHE
    if LOCATION_CACHE is not None:
        return LOCATION_CACHE
    try:
        with urlopen(LOCATION_API_URL, timeout=3) as response:
            LOCATION_CACHE = json.loads(response.read().decode("utf-8"))
    except Exception:
        LOCATION_CACHE = FALLBACK_LOCATIONS
    return LOCATION_CACHE

def _validate_location_selection(province, province_code, district, district_code, ward, ward_code):
    if not all([province, province_code, district, district_code, ward, ward_code]):
        raise HTTPException(status_code=400, detail="Vui lòng chọn đầy đủ Tỉnh/Thành phố, Quận/Huyện và Phường/Xã")
    for province_item in _get_locations():
        if str(province_item["code"]) == str(province_code) and province_item["name"] == province:
            for district_item in province_item.get("districts", []):
                if str(district_item["code"]) == str(district_code) and district_item["name"] == district:
                    if any(str(ward_item["code"]) == str(ward_code) and ward_item["name"] == ward for ward_item in district_item.get("wards", [])):
                        return
    raise HTTPException(status_code=400, detail="Địa chỉ Tỉnh/Thành phố, Quận/Huyện hoặc Phường/Xã không hợp lệ")

def _shipping_method(code: str):
    method = SHIPPING_METHODS.get((code or "").upper())
    if not method:
        raise HTTPException(status_code=400, detail="Phương thức vận chuyển không hợp lệ")
    return method

def _validate_payment_method(method: str):
    normalized = (method or "").upper()
    if normalized not in PAYMENT_METHODS:
        raise HTTPException(status_code=400, detail="Phương thức thanh toán không được hỗ trợ")
    return normalized

def _calculate_discount(db: Session, user_id: int, code: str | None, subtotal: float):
    if not code:
        return None, 0.0
    voucher = db.query(models.Voucher).filter(models.Voucher.code == code.strip().upper()).first()
    now = datetime.utcnow()
    if not voucher or not voucher.is_active:
        raise HTTPException(status_code=400, detail="Voucher không tồn tại hoặc đã bị khóa")
    if voucher.starts_at and voucher.starts_at > now or voucher.expires_at and voucher.expires_at < now:
        raise HTTPException(status_code=400, detail="Voucher đã hết hạn hoặc chưa đến thời gian sử dụng")
    if voucher.usage_limit is not None and voucher.used_count >= voucher.usage_limit:
        raise HTTPException(status_code=400, detail="Voucher đã hết lượt sử dụng")
    if subtotal < voucher.min_order_amount:
        raise HTTPException(status_code=400, detail=f"Đơn hàng tối thiểu {voucher.min_order_amount:,.0f}đ để dùng voucher này")
    if db.query(models.VoucherUsage).filter_by(voucher_id=voucher.id, user_id=user_id).first():
        raise HTTPException(status_code=400, detail="Bạn đã sử dụng voucher này trước đó")
    discount = voucher.discount_value if voucher.discount_type == "FIXED" else subtotal * voucher.discount_value / 100
    if voucher.max_discount is not None:
        discount = min(discount, voucher.max_discount)
    return voucher, min(discount, subtotal)


def _calculate_order_snapshot(db: Session, user_id: int, items: list[schemas.CartItemInput], shipping_name: str, shipping_phone: str, shipping_address: str, payment_method: str, shipping_method: str, voucher_code: str | None):
    total_amount = 0.0
    item_snapshot = []

    for item in items:
        book = db.query(models.Book).filter(models.Book.id == item.book_id).first()
        if not book:
            raise HTTPException(status_code=404, detail=f"Sách #{item.book_id} không tồn tại")
        if book.status != models.BookStatus.APPROVED.value or not getattr(book, 'is_visible', True) or getattr(book, 'is_out_of_stock', False):
            raise HTTPException(status_code=400, detail=f"Cuốn sách '{book.title}' hiện đã hết hàng hoặc tạm khóa bởi NXB")
        if item.quantity <= 0:
            raise HTTPException(status_code=400, detail=f"Số lượng cho sách '{book.title}' phải lớn hơn 0")
        if book.stock < item.quantity:
            raise HTTPException(status_code=400, detail=f"Sách '{book.title}' chỉ còn {book.stock} cuốn trong kho")

        unit_price = book.discount_price if (book.discount_price and book.discount_price > 0) else book.price
        subtotal = unit_price * item.quantity
        total_amount += subtotal

        item_snapshot.append({
            "book_id": book.id,
            "title": book.title,
            "cover_image": book.cover_image,
            "seller_id": book.seller_id,
            "quantity": item.quantity,
            "price": unit_price,
            "total_price": subtotal,
        })

    shipping = _shipping_method(shipping_method)
    payment = _validate_payment_method(payment_method)
    voucher, discount_amount = _calculate_discount(db, user_id, voucher_code, total_amount)
    shipping_fee = shipping["fee"]
    grand_total = max(0.0, total_amount + shipping_fee - discount_amount)

    return {
        "items": item_snapshot,
        "subtotal": total_amount,
        "shipping_fee": shipping_fee,
        "total_amount": grand_total,
            "subtotal": total_amount,
        "shipping_name": shipping_name,
        "shipping_phone": shipping_phone,
        "shipping_address": shipping_address,
        "payment_method": payment,
        "shipping_method": shipping_method.upper(),
        "shipping_fee": shipping_fee,
        "discount_amount": discount_amount,
        "voucher": voucher,
    }

@router.get("/shipping-methods", response_model=List[schemas.ShippingMethodOut])
def get_shipping_methods():
    return [{"code": code, **data} for code, data in SHIPPING_METHODS.items()]

@router.get("/locations")
def get_locations():
    return {"source": LOCATION_API_URL, "locations": _get_locations()}

@router.get("/locations/provinces")
def get_provinces():
    return [{"code": item["code"], "name": item["name"]} for item in _get_locations()]

@router.get("/locations/districts/{province_code}")
def get_districts(province_code: str):
    province = next((item for item in _get_locations() if str(item["code"]) == str(province_code)), None)
    if not province:
        raise HTTPException(status_code=404, detail="Không tìm thấy Tỉnh/Thành phố")
    return [{"code": item["code"], "name": item["name"]} for item in province.get("districts", [])]

@router.get("/locations/wards/{district_code}")
def get_wards(district_code: str):
    for province in _get_locations():
        district = next((item for item in province.get("districts", []) if str(item["code"]) == str(district_code)), None)
        if district:
            return [{"code": item["code"], "name": item["name"]} for item in district.get("wards", [])]
    raise HTTPException(status_code=404, detail="Không tìm thấy Quận/Huyện")

@router.get("/addresses", response_model=List[schemas.AddressOut])
def get_addresses(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    return db.query(models.Address).filter_by(user_id=current_user.id).order_by(models.Address.is_default.desc(), models.Address.id.desc()).all()

@router.post("/addresses", response_model=schemas.AddressOut)
def create_address(address_in: schemas.AddressCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    _validate_location_selection(address_in.province, address_in.province_code, address_in.district, address_in.district_code, address_in.ward, address_in.ward_code)
    if address_in.is_default:
        db.query(models.Address).filter_by(user_id=current_user.id).update({"is_default": False})
    address = models.Address(user_id=current_user.id, **address_in.model_dump())
    db.add(address)
    db.commit()
    db.refresh(address)
    return address

@router.patch("/addresses/{address_id}", response_model=schemas.AddressOut)
def update_address(address_id: int, address_in: schemas.AddressUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    address = db.query(models.Address).filter_by(id=address_id, user_id=current_user.id).first()
    if not address:
        raise HTTPException(status_code=404, detail="Không tìm thấy địa chỉ")
    values = address_in.model_dump(exclude_unset=True)
    candidate = {field: values.get(field, getattr(address, field)) for field in ["province", "province_code", "district", "district_code", "ward", "ward_code"]}
    _validate_location_selection(candidate["province"], candidate["province_code"], candidate["district"], candidate["district_code"], candidate["ward"], candidate["ward_code"])
    if values.get("is_default"):
        db.query(models.Address).filter_by(user_id=current_user.id).update({"is_default": False})
    for key, value in values.items():
        setattr(address, key, value)
    db.commit()
    db.refresh(address)
    return address

@router.delete("/addresses/{address_id}")
def delete_address(address_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    address = db.query(models.Address).filter_by(id=address_id, user_id=current_user.id).first()
    if not address:
        raise HTTPException(status_code=404, detail="Không tìm thấy địa chỉ")
    db.delete(address)
    db.commit()
    return {"message": "Đã xóa địa chỉ"}

@router.post("/vouchers/apply", response_model=schemas.VoucherApplyOut)
def apply_voucher(voucher_in: schemas.VoucherApplyRequest, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    voucher, discount = _calculate_discount(db, current_user.id, voucher_in.code, voucher_in.subtotal)
    return {"code": voucher.code, "name": voucher.name, "discount_amount": discount}

@router.get("/vouchers/available")
def get_available_vouchers(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    now = datetime.utcnow()
    vouchers = db.query(models.Voucher).filter(
        models.Voucher.is_active.is_(True),
        models.Voucher.starts_at <= now,
        (models.Voucher.expires_at.is_(None) | (models.Voucher.expires_at >= now)),
        (models.Voucher.usage_limit.is_(None) | (models.Voucher.used_count < models.Voucher.usage_limit)),
    ).order_by(models.Voucher.id.desc()).all()
    return [{"code": voucher.code, "name": voucher.name, "min_order_amount": voucher.min_order_amount} for voucher in vouchers]


@router.post("/checkout/instant", response_model=schemas.CheckoutDraftOut)
def create_instant_checkout(
    checkout_in: schemas.CheckoutInstantRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    if not checkout_in.book_id:
        raise HTTPException(status_code=400, detail="Thiếu thông tin sách cần mua")

    if checkout_in.quantity <= 0:
        raise HTTPException(status_code=400, detail="Số lượng mua tối thiểu là 1")

    book = db.query(models.Book).filter(models.Book.id == checkout_in.book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Không tìm thấy sách")
    if book.status != models.BookStatus.APPROVED.value:
        raise HTTPException(status_code=400, detail=f"Cuốn sách '{book.title}' hiện chưa được mở bán")
    if book.stock < checkout_in.quantity:
        raise HTTPException(status_code=400, detail=f"Sách '{book.title}' chỉ còn {book.stock} cuốn trong kho")

    shipping_name = checkout_in.shipping_name or current_user.full_name or current_user.username
    shipping_phone = checkout_in.shipping_phone or current_user.phone or ""
    shipping_address = checkout_in.shipping_address or current_user.address or ""

    unit_price = book.discount_price if (book.discount_price and book.discount_price > 0) else book.price
    subtotal = unit_price * checkout_in.quantity
    shipping = _shipping_method(checkout_in.shipping_method)
    _validate_payment_method(checkout_in.payment_method)
    voucher, discount_amount = _calculate_discount(db, current_user.id, checkout_in.voucher_code, subtotal)
    shipping_fee = shipping["fee"]
    total_amount = max(0.0, subtotal + shipping_fee - discount_amount)

    return {
        "book_id": book.id,
        "title": book.title,
        "author": book.author,
        "cover_image": book.cover_image,
        "seller_id": book.seller_id,
        "quantity": checkout_in.quantity,
        "stock": book.stock,
        "unit_price": unit_price,
        "subtotal": subtotal,
        "shipping_fee": shipping_fee,
        "total_amount": total_amount,
        "shipping_name": shipping_name,
        "shipping_phone": shipping_phone,
        "shipping_address": shipping_address,
        "payment_method": checkout_in.payment_method,
        "shipping_method": checkout_in.shipping_method.upper(),
        "shipping_fee": shipping_fee,
        "discount_amount": discount_amount,
        "voucher_code": voucher.code if voucher else None,
        "items": [{
            "book_id": book.id,
            "title": book.title,
            "cover_image": book.cover_image,
            "seller_id": book.seller_id,
            "quantity": checkout_in.quantity,
            "price": unit_price,
            "total_price": subtotal,
        }],
    }


@router.post("", response_model=schemas.OrderOut)
def create_order(
    order_in: schemas.OrderCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    if not order_in.items:
        raise HTTPException(status_code=400, detail="Giỏ hàng đang trống")

    if not order_in.terms_accepted:
        raise HTTPException(status_code=400, detail="Vui lòng đồng ý với Điều khoản dịch vụ và Chính sách mua hàng")
    if not order_in.shipping_name or not order_in.shipping_phone or not order_in.shipping_address:
        raise HTTPException(status_code=400, detail="Vui lòng điền đầy đủ thông tin nhận hàng")
    _validate_location_selection(order_in.shipping_province, order_in.shipping_province_code, order_in.shipping_district, order_in.shipping_district_code, order_in.shipping_ward, order_in.shipping_ward_code)

    order_snapshot = _calculate_order_snapshot(
        db, current_user.id,
        order_in.items,
        order_in.shipping_name,
        order_in.shipping_phone,
        order_in.shipping_address,
        order_in.payment_method,
        order_in.shipping_method,
        order_in.voucher_code,
    )

    total_amount = order_snapshot["total_amount"]
    items_to_create = []

    for item in order_snapshot["items"]:
        book = db.query(models.Book).filter(models.Book.id == item["book_id"]).first()
        if not book:
            raise HTTPException(status_code=404, detail=f"Sách #{item['book_id']} không tồn tại")

        book.stock -= item["quantity"]
        book.sold_count += item["quantity"]

        order_item = models.OrderItem(
            book_id=book.id,
            seller_id=book.seller_id,
            quantity=item["quantity"],
            price=item["price"],
            book_title=book.title,
            book_cover=book.cover_image
        )
        items_to_create.append(order_item)

    platform_fee = calculate_commission(order_snapshot["subtotal"])
    seller_payout = order_snapshot["subtotal"] - platform_fee

    order_code = f"BH-{datetime.utcnow().strftime('%y%m%d')}-{str(uuid.uuid4())[:6].upper()}"

    new_order = models.Order(
        order_code=order_code,
        buyer_id=current_user.id,
        total_amount=total_amount,
        platform_fee_percent=PLATFORM_COMMISSION_RATE,
        platform_fee_amount=platform_fee,
        seller_payout_amount=seller_payout,
        shipping_name=order_snapshot["shipping_name"],
        shipping_phone=order_snapshot["shipping_phone"],
        shipping_address=order_snapshot["shipping_address"],
        shipping_province=order_in.shipping_province,
        shipping_province_code=order_in.shipping_province_code,
        shipping_district=order_in.shipping_district,
        shipping_district_code=order_in.shipping_district_code,
        shipping_ward=order_in.shipping_ward,
        shipping_ward_code=order_in.shipping_ward_code,
        shipping_street=order_in.shipping_street,
        shipping_method=order_snapshot["shipping_method"],
        shipping_fee=order_snapshot["shipping_fee"],
        subtotal_amount=order_snapshot["subtotal"],
        discount_amount=order_snapshot["discount_amount"],
        voucher_code=order_snapshot["voucher"].code if order_snapshot["voucher"] else None,
        terms_accepted=True,
        payment_method=order_snapshot["payment_method"],
        payment_status=models.PaymentStatus.PAID.value if order_snapshot["payment_method"] == "COD" else models.PaymentStatus.PENDING.value,
        notes=order_in.notes,
        status=models.OrderStatus.PENDING.value,
        tracking_step=1,
    )

    db.add(new_order)
    db.flush()

    voucher = order_snapshot["voucher"]
    if voucher:
        voucher.used_count += 1
        db.add(models.VoucherUsage(voucher_id=voucher.id, user_id=current_user.id, order_id=new_order.id))

    for item in items_to_create:
        item.order_id = new_order.id
        db.add(item)

    db.commit()
    db.refresh(new_order)

    # 📲 Gửi thông báo Giai đoạn 1: Đặt hàng thành công
    try:
        notification_service.notify_order_created(db, new_order, current_user)
    except Exception:
        pass  # Không để lỗi thông báo ảnh hưởng tới luồng đặt hàng

    return new_order

@router.get("/my-orders", response_model=List[schemas.OrderOut])
def get_my_orders(
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(auth.get_current_user)
):
    orders = db.query(models.Order).filter(
        models.Order.buyer_id == current_user.id
    ).order_by(models.Order.created_at.desc()).all()
    return orders

@router.get("/{order_id:int}", response_model=schemas.OrderOut)
def get_order_detail(
    order_id: int, 
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(auth.get_current_user)
):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng")
    
    # Cho phép Buyer, Seller của món hàng, hoặc Admin xem
    if order.buyer_id != current_user.id and current_user.role == models.UserRole.SELLER.value and not any(item.seller_id == current_user.id for item in order.items):
        raise HTTPException(status_code=403, detail="Không có quyền xem đơn hàng này")
    if order.buyer_id != current_user.id and current_user.role not in [models.UserRole.ADMIN.value, models.UserRole.SELLER.value]:
        raise HTTPException(status_code=403, detail="Không có quyền xem đơn hàng này")
    
    return order

@router.post("/{order_id:int}/confirm-received", response_model=schemas.OrderOut)
def confirm_order_received(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng")
    if order.buyer_id != current_user.id and current_user.role not in [models.UserRole.ADMIN.value]:
        raise HTTPException(status_code=403, detail="Bạn không có quyền thao tác trên đơn hàng này")
    if order.status == models.OrderStatus.DELIVERED.value:
        return order
    if order.status == models.OrderStatus.CANCELLED.value:
        raise HTTPException(status_code=400, detail="Không thể xác nhận đơn hàng đã bị hủy")

    order.status = models.OrderStatus.DELIVERED.value
    order.tracking_step = 4
    if order.payment_method == "COD":
        order.payment_status = models.PaymentStatus.PAID.value
    order.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(order)

    # ✅ Gửi thông báo Giai đoạn 3: Xác nhận nhận hàng
    try:
        notification_service.notify_order_delivered(db, order, current_user)
    except Exception:
        pass  # Không để lỗi thông báo ảnh hưởng tới luồng xác nhận

    return order
