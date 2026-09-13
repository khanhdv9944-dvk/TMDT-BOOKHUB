from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from database import get_db
import models, schemas, auth

BASE_DIR = Path(__file__).resolve().parent.parent
DOCUMENT_STORAGE_DIR = BASE_DIR / "uploads" / "documents"
DOCUMENT_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

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
def update_current_user_profile(
    profile: schemas.UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    for field, value in profile.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/seller/upload-document", response_model=schemas.DocumentOut)
def upload_seller_document(
    file: UploadFile = File(...),
    document_type: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.UserRole.SELLER.value, models.UserRole.ADMIN.value]))
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Vui lòng chọn tệp giấy tờ hợp lệ")

    allowed_types = {"BUSINESS_LICENSE", "PUBLISHER_LICENSE"}
    if document_type.upper() not in allowed_types:
        raise HTTPException(status_code=400, detail="Loại giấy tờ không hợp lệ")

    suffix = Path(file.filename).suffix.lower() or ".bin"
    if suffix not in {".pdf", ".jpg", ".jpeg", ".png"}:
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận PDF, JPG, JPEG, PNG")

    file_bytes = file.file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Tệp tin rỗng")
    if len(file_bytes) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Dung lượng file tối đa là 5MB")

    safe_name = f"{uuid4().hex}{suffix}"
    target_path = DOCUMENT_STORAGE_DIR / safe_name
    with open(target_path, "wb") as output_file:
        output_file.write(file_bytes)

    stored_document = models.Document(
        owner_id=current_user.id,
        entity_type="SELLER",
        entity_id=current_user.id,
        document_type=document_type.upper(),
        file_name=file.filename,
        mime_type=file.content_type or "application/octet-stream",
        storage_path=str(target_path.resolve()),
        status="UPLOADED"
    )
    db.add(stored_document)
    db.commit()
    db.refresh(stored_document)

    if document_type.upper() == "BUSINESS_LICENSE":
        current_user.business_license = file.filename
        db.commit()

    return stored_document

@router.post("/seller/verification")
def submit_seller_verification(
    payload: schemas.SellerVerificationRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.UserRole.SELLER.value]))
):
    current_user.business_type = payload.business_type
    current_user.company_name = payload.company_name
    current_user.tax_code = payload.tax_code
    current_user.company_email = payload.company_email
    current_user.company_phone = payload.company_phone
    current_user.legal_representative_name = payload.legal_representative_name
    current_user.legal_representative_position = payload.legal_representative_position
    current_user.legal_representative_id_number = payload.legal_representative_id_number
    current_user.office_province = payload.office_province
    current_user.office_district = payload.office_district
    current_user.office_ward = payload.office_ward
    current_user.office_street = payload.office_street
    current_user.shipping_same_as_office = payload.shipping_same_as_office
    current_user.shipping_province = payload.shipping_province
    current_user.shipping_district = payload.shipping_district
    current_user.shipping_ward = payload.shipping_ward
    current_user.shipping_street = payload.shipping_street
    current_user.bank_name = payload.bank_name
    current_user.bank_account_number = payload.bank_account_number
    current_user.bank_account_holder = payload.bank_account_holder
    current_user.shop_name = current_user.shop_name or payload.company_name
    current_user.status = models.UserStatus.PENDING_SELLER_APPROVAL.value

    if payload.documents:
        referenced_ids = [item.document_id for item in payload.documents if item.document_id]
        if referenced_ids:
            first_document = db.query(models.Document).filter(models.Document.id.in_(referenced_ids), models.Document.owner_id == current_user.id).first()
            if first_document:
                current_user.business_license = first_document.file_name

    db.commit()
    db.refresh(current_user)
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
