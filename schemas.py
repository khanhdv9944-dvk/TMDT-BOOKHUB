from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

# User Schemas
class UserBase(BaseModel):
    username: str
    email: str
    full_name: Optional[str] = None

    role: str = "BUYER"
    phone: Optional[str] = None
    address: Optional[str] = None
    shop_name: Optional[str] = None
    shop_description: Optional[str] = None
    business_license: Optional[str] = None
    tax_code: Optional[str] = None
    bank_name: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_account_holder: Optional[str] = None
    warehouse_address: Optional[str] = None
    shop_logo: Optional[str] = None
    shop_banner: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    username: str
    password: str


class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    avatar: Optional[str] = None

class UserOut(UserBase):
    id: int
    status: str
    avatar: Optional[str] = None
    seller_balance: float = 0.0
    vip_expires_at: Optional[datetime] = None
    is_vip: bool = False
    created_at: datetime
    rejection_reason: Optional[str] = None

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserOut

# Category Schemas
class CategoryOut(BaseModel):
    id: int
    name: str
    slug: str
    icon: Optional[str] = "book"
    description: Optional[str] = None

    class Config:
        from_attributes = True

# Book Schemas
class BookBase(BaseModel):
    title: str
    author: str
    publisher: Optional[str] = None
    category_id: int
    price: float
    discount_price: Optional[float] = None
    stock: int = 10
    cover_image: Optional[str] = None
    description: Optional[str] = None
    book_format: str = "PAPER"
    cover_type: str = "SOFT"
    vip_eligible: bool = False
    isbn: Optional[str] = None
    translator: Optional[str] = None
    page_count: Optional[int] = None
    publication_year: Optional[int] = None
    language: Optional[str] = "Tiếng Việt"
    preview_file_url: Optional[str] = None
    sample_content: Optional[str] = None
    full_ebook_content: Optional[str] = None

class BookCreate(BookBase):
    pass

class BookUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    publisher: Optional[str] = None
    category_id: Optional[int] = None
    price: Optional[float] = None
    discount_price: Optional[float] = None
    stock: Optional[int] = None
    cover_image: Optional[str] = None
    description: Optional[str] = None
    book_format: Optional[str] = None
    cover_type: Optional[str] = None
    vip_eligible: Optional[bool] = None
    isbn: Optional[str] = None
    translator: Optional[str] = None
    page_count: Optional[int] = None
    publication_year: Optional[int] = None
    language: Optional[str] = None
    preview_file_url: Optional[str] = None
    sample_content: Optional[str] = None
    full_ebook_content: Optional[str] = None

class BookOut(BookBase):
    id: int
    seller_id: int
    status: str
    is_featured_ad: bool
    sold_count: int
    rating: float
    created_at: datetime
    seller_shop_name: Optional[str] = None
    category_name: Optional[str] = None
    is_visible: bool = True
    rejection_reason: Optional[str] = None

    class Config:
        from_attributes = True

# Order Schemas
class CartItemInput(BaseModel):
    book_id: int
    quantity: int

class CheckoutInstantRequest(BaseModel):
    book_id: int
    quantity: int = 1
    shipping_name: Optional[str] = None
    shipping_phone: Optional[str] = None
    shipping_address: Optional[str] = None
    payment_method: str = "COD"
    shipping_method: str = "STANDARD"
    voucher_code: Optional[str] = None
    terms_accepted: bool = False
    shipping_province: Optional[str] = None
    shipping_province_code: Optional[str] = None
    shipping_district: Optional[str] = None
    shipping_district_code: Optional[str] = None
    shipping_ward: Optional[str] = None
    shipping_ward_code: Optional[str] = None
    shipping_street: Optional[str] = None

class OrderCreate(BaseModel):
    items: List[CartItemInput]
    shipping_name: str
    shipping_phone: str
    shipping_address: str
    payment_method: str = "COD"
    notes: Optional[str] = None
    shipping_method: str = "STANDARD"
    voucher_code: Optional[str] = None
    terms_accepted: bool = False
    shipping_province: Optional[str] = None
    shipping_province_code: Optional[str] = None
    shipping_district: Optional[str] = None
    shipping_district_code: Optional[str] = None
    shipping_ward: Optional[str] = None
    shipping_ward_code: Optional[str] = None
    shipping_street: Optional[str] = None

class AddressCreate(BaseModel):
    recipient_name: str
    phone: str
    province: str
    district: str
    ward: str
    street: str
    province_code: Optional[str] = None
    district_code: Optional[str] = None
    ward_code: Optional[str] = None
    is_default: bool = False

class AddressUpdate(BaseModel):
    recipient_name: Optional[str] = None
    phone: Optional[str] = None
    province: Optional[str] = None
    province_code: Optional[str] = None
    district: Optional[str] = None
    district_code: Optional[str] = None
    ward: Optional[str] = None
    ward_code: Optional[str] = None
    street: Optional[str] = None
    is_default: Optional[bool] = None

class AddressOut(AddressCreate):
    id: int
    class Config:
        from_attributes = True

class VoucherApplyRequest(BaseModel):
    code: str
    subtotal: float = 0.0

class VoucherApplyOut(BaseModel):
    code: str
    name: str
    discount_amount: float

class ShippingMethodOut(BaseModel):
    code: str
    name: str
    description: str
    fee: float
    delivery_estimate: str

class CheckoutItemOut(BaseModel):
    book_id: int
    title: str
    cover_image: Optional[str]
    seller_id: int
    quantity: int
    price: float
    total_price: float

class CheckoutDraftOut(BaseModel):
    book_id: int
    title: str
    author: str
    cover_image: Optional[str]
    seller_id: int
    quantity: int
    stock: int = 1
    unit_price: float
    subtotal: float
    shipping_fee: float
    total_amount: float
    shipping_name: str
    shipping_phone: str
    shipping_address: str
    payment_method: str
    shipping_method: str = "STANDARD"
    discount_amount: float = 0.0
    voucher_code: Optional[str] = None
    items: List[CheckoutItemOut] = []

    class Config:
        from_attributes = True

class OrderItemOut(BaseModel):
    id: int
    book_id: int
    seller_id: int
    book_title: Optional[str]
    book_cover: Optional[str]
    quantity: int
    price: float

    class Config:
        from_attributes = True

class OrderOut(BaseModel):
    id: int
    order_code: str
    buyer_id: int
    total_amount: float
    platform_fee_percent: float
    platform_fee_amount: float
    seller_payout_amount: float
    shipping_name: str
    shipping_phone: str
    shipping_address: str
    shipping_carrier: str
    tracking_number: Optional[str] = None
    tracking_step: int
    payment_method: str
    payment_status: str
    status: str
    return_status: Optional[str] = "NONE"
    return_reason: Optional[str] = None
    notes: Optional[str]
    subtotal_amount: float = 0.0
    shipping_fee: float = 0.0
    discount_amount: float = 0.0
    voucher_code: Optional[str] = None
    shipping_method: str = "STANDARD"
    created_at: datetime
    items: List[OrderItemOut] = []

    class Config:
        from_attributes = True

# VIP Subscription
class VipPurchaseRequest(BaseModel):
    plan_name: str # 1_MONTH, 6_MONTHS, 1_YEAR
    price: float
    duration_days: int

# Ad Purchase
class AdPurchaseRequest(BaseModel):
    book_id: int
    duration_days: int
    fee_paid: float

# Merchant Profile Update
class SellerProfileUpdate(BaseModel):
    shop_name: Optional[str] = None
    shop_description: Optional[str] = None
    phone: Optional[str] = None
    warehouse_address: Optional[str] = None
    shop_logo: Optional[str] = None
    shop_banner: Optional[str] = None
    tax_code: Optional[str] = None
    bank_name: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_account_holder: Optional[str] = None

# Shop Voucher Schemas
class ShopVoucherCreate(BaseModel):
    code: str
    name: str
    discount_type: str = "PERCENT" # PERCENT, FIXED
    discount_value: float
    max_discount: Optional[float] = None
    min_order_amount: float = 0.0
    usage_limit: Optional[int] = 100
    expires_at: Optional[datetime] = None

class ShopVoucherOut(BaseModel):
    id: int
    seller_id: Optional[int]
    code: str
    name: str
    discount_type: str
    discount_value: float
    max_discount: Optional[float]
    min_order_amount: float
    usage_limit: Optional[int]
    used_count: int
    is_active: bool
    starts_at: datetime
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True

# Withdrawal Schemas
class WithdrawalRequestCreate(BaseModel):
    amount: float
    bank_name: str
    bank_account_number: str
    bank_account_holder: str
    note: Optional[str] = None

class WithdrawalRequestOut(BaseModel):
    id: int
    seller_id: int
    amount: float
    bank_name: str
    bank_account_number: str
    bank_account_holder: str
    status: str
    note: Optional[str]
    created_at: datetime
    rejection_reason: Optional[str] = None
    processed_at: Optional[datetime] = None
    transaction_id: Optional[str] = None

    class Config:
        from_attributes = True


class AdminReason(BaseModel):
    reason: str


class AdminDisputeCreate(BaseModel):
    order_id: int
    reason: str
    description: str
    amount: float = 0.0


class DisputeOut(BaseModel):
    id: int
    dispute_code: str
    order_id: int
    buyer_id: int
    seller_id: int
    reason: str
    description: str
    amount: float
    status: str
    buyer_response: Optional[str] = None
    seller_response: Optional[str] = None
    admin_decision: Optional[str] = None
    resolution_note: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DisputeDecision(BaseModel):
    decision: str
    note: Optional[str] = None


class DocumentOut(BaseModel):
    id: int
    owner_id: int
    entity_type: str
    entity_id: int
    document_type: str
    file_name: str
    mime_type: str
    uploaded_at: datetime
    status: str

    class Config:
        from_attributes = True

# Seller Staff Schemas
class SellerStaffCreate(BaseModel):
    staff_name: str
    staff_email: str
    staff_phone: Optional[str] = None
    role: str = "WAREHOUSE" # WAREHOUSE, MARKETING, ACCOUNTANT

class SellerStaffOut(BaseModel):
    id: int
    seller_id: int
    staff_name: str
    staff_email: str
    staff_phone: Optional[str]
    role: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

# Order Management
class SellerOrderUpdateStatus(BaseModel):
    new_status: str # PACKING, SHIPPING, DELIVERED, CANCELLED
    tracking_carrier: Optional[str] = "Giao Hàng Nhanh (GHN Express)"
    tracking_number: Optional[str] = None

class SellerOrderReturnAction(BaseModel):
    action: str # APPROVE, REJECT
    note: Optional[str] = None

class SellerQuickStockUpdate(BaseModel):
    stock: int

class SellerBulkOrderConfirm(BaseModel):
    order_ids: List[int]
