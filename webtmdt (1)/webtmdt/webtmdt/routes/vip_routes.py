from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models, schemas, auth

router = APIRouter(prefix="/api/vip", tags=["VIP Subscription"])

VIP_PLANS = [
    {
        "id": "vip_1m",
        "name": "Gói VIP Khám Phá (1 Tháng)",
        "price": 49000,
        "duration_days": 30,
        "features": ["Đọc toàn bộ 10,000+ Ebook bản quyền", "Nghe sách nói Audiobook chất lượng cao", "Không có quảng cáo gián đoạn", "Tải đọc offline"]
    },
    {
        "id": "vip_6m",
        "name": "Gói VIP Tri Thức (6 Tháng)",
        "price": 249000,
        "duration_days": 180,
        "popular": True,
        "features": ["Mọi quyền lợi gói 1 Tháng", "Tiết kiệm 15% chi phí", "Tặng 2 Voucher giảm 20% khi mua sách giấy", "Huy hiệu Độc giả Ưu tú"]
    },
    {
        "id": "vip_12m",
        "name": "Gói VIP Hoàng Gia (1 Năm)",
        "price": 449000,
        "duration_days": 365,
        "features": ["Mọi quyền lợi cao cấp nhất", "Tiết kiệm 30% chi phí", "Tặng 5 Voucher mua sách giấy", "Tham gia CLB Đọc sách tác giả độc quyền"]
    }
]

@router.get("/plans")
def get_vip_plans():
    return VIP_PLANS

@router.post("/subscribe")
def subscribe_vip(
    plan_in: schemas.VipPurchaseRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    now = datetime.utcnow()
    # Nếu đang là VIP thì cộng dồn ngày, nếu chưa thì tính từ bây giờ
    start_date = now
    if current_user.vip_expires_at and current_user.vip_expires_at > now:
        start_date = current_user.vip_expires_at
    
    end_date = start_date + timedelta(days=plan_in.duration_days)
    current_user.vip_expires_at = end_date

    sub = models.VipSubscription(
        user_id=current_user.id,
        plan_name=plan_in.plan_name,
        price=plan_in.price,
        duration_days=plan_in.duration_days,
        start_date=start_date,
        end_date=end_date
    )
    db.add(sub)
    db.commit()
    db.refresh(current_user)

    return {
        "message": f"Chúc mừng bạn đã nâng cấp thành công {plan_in.plan_name}!",
        "vip_expires_at": current_user.vip_expires_at,
        "is_vip": True
    }
