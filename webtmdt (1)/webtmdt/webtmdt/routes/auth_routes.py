from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
import models, schemas, auth

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/register", response_model=schemas.Token)
def register(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    if user_data.role not in {models.UserRole.BUYER.value, models.UserRole.SELLER.value}:
        raise HTTPException(status_code=400, detail="Chỉ cho phép đăng ký tài khoản Buyer hoặc Seller")
    # Check duplicate username
    if db.query(models.User).filter(models.User.username == user_data.username).first():
        raise HTTPException(status_code=400, detail="Tên đăng nhập đã tồn tại")
    
    # Check duplicate email
    if db.query(models.User).filter(models.User.email == user_data.email).first():
        raise HTTPException(status_code=400, detail="Email này đã được sử dụng")
    
    # Seller registration default status is PENDING_SELLER_APPROVAL if needed or ACTIVE
    initial_status = models.UserStatus.PENDING_SELLER_APPROVAL.value if user_data.role == models.UserRole.SELLER.value else models.UserStatus.ACTIVE.value
    
    new_user = models.User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=auth.get_password_hash(user_data.password),
        full_name=user_data.full_name or user_data.username,
        role=user_data.role,
        status=initial_status,
        phone=user_data.phone,
        address=user_data.address,
        shop_name=user_data.shop_name,
        shop_description=user_data.shop_description,
        business_license=user_data.business_license,
        avatar=f"https://api.dicebear.com/7.x/bottts/svg?seed={user_data.username}"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = auth.create_access_token(data={"sub": new_user.username, "role": new_user.role})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": new_user
    }

@router.post("/login", response_model=schemas.Token)
def login(login_data: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(
        (models.User.username == login_data.username) | (models.User.email == login_data.username)
    ).first()

    if not user or not auth.verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tài khoản hoặc mật khẩu không chính xác"
        )
    
    if user.status == models.UserStatus.BANNED.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản này đã bị khóa do vi phạm chính sách của sàn TMĐT!"
        )

    token = auth.create_access_token(data={"sub": user.username, "role": user.role})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user
    }

@router.get("/me", response_model=schemas.UserOut)
def get_current_user_profile(current_user: models.User = Depends(auth.get_current_user)):
    return current_user


@router.patch("/me", response_model=schemas.UserOut)
def update_current_user_profile(profile: schemas.UserProfileUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    for field, value in profile.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return current_user

@router.post("/demo-switch-user")
def demo_switch_user(username: str, db: Session = Depends(get_db)):
    """Tiện ích chuyển đổi nhanh tài khoản mẫu để trình diễn 3 vai trò"""
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản demo")
    
    token = auth.create_access_token(data={"sub": user.username, "role": user.role})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "status": user.status,
            "avatar": user.avatar,
            "shop_name": user.shop_name,
            "is_vip": user.is_vip,
            "seller_balance": user.seller_balance
        }
    }
