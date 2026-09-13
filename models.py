from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Enum, UniqueConstraint
from sqlalchemy.orm import relationship
from database import Base
import enum

class UserRole(str, enum.Enum):
    BUYER = "BUYER"
    SELLER = "SELLER"
    ADMIN = "ADMIN"

class UserStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    BANNED = "BANNED"
    DRAFT = "DRAFT"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PENDING_SELLER_APPROVAL = "PENDING_SELLER_APPROVAL"

class BookStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class OrderStatus(str, enum.Enum):
    PENDING = "PENDING"          # Khách vừa đặt
    PACKING = "PACKING"          # NXB đã bấm Xác nhận đóng gói
    SHIPPING = "SHIPPING"        # Đang vận chuyển
    DELIVERED = "DELIVERED"      # Đã giao thành công
    CANCELLED = "CANCELLED"      # Đã hủy

class PaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class NotificationType(str, enum.Enum):
    NEW_BOOK_SUBMITTED = "NEW_BOOK_SUBMITTED"
    BOOK_APPROVED = "BOOK_APPROVED"
    BOOK_REJECTED = "BOOK_REJECTED"
    ORDER_CREATED = "ORDER_CREATED"
    ORDER_PACKING = "ORDER_PACKING"
    ORDER_SHIPPING = "ORDER_SHIPPING"
    ORDER_OUT_FOR_DELIVERY = "ORDER_OUT_FOR_DELIVERY"
    ORDER_DELIVERED = "ORDER_DELIVERED"
    ORDER_REVIEWED = "ORDER_REVIEWED"
    RETURN_REQUESTED = "RETURN_REQUESTED"
    RETURN_UPDATED = "RETURN_UPDATED"
    PAYOUT_APPROVED = "PAYOUT_APPROVED"
    PAYOUT_REJECTED = "PAYOUT_REJECTED"
    LOW_STOCK_ALERT = "LOW_STOCK_ALERT"
    SYSTEM_ANNOUNCEMENT = "SYSTEM_ANNOUNCEMENT"

class ReturnRequestStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    CUSTOMER_SHIPPED = "CUSTOMER_SHIPPED"
    RECEIVED = "RECEIVED"
    REFUND_PROCESSING = "REFUND_PROCESSING"
    REFUNDED = "REFUNDED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"

class ReviewStatus(str, enum.Enum):
    NOT_REVIEWED = "NOT_REVIEWED"
    REVIEWED = "REVIEWED"
    EDITED = "EDITED"
    HIDDEN = "HIDDEN"

class ReturnReason(str, enum.Enum):
    PRODUCT_DEFECT = "PRODUCT_DEFECT"
    WRONG_PRODUCT = "WRONG_PRODUCT"
    DESCRIPTION_MISMATCH = "DESCRIPTION_MISMATCH"
    MISSING_ITEM = "MISSING_ITEM"
    CHANGE_OF_MIND = "CHANGE_OF_MIND"
    OTHER = "OTHER"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=True)
    role = Column(String(20), default=UserRole.BUYER.value)
    status = Column(String(30), default=UserStatus.ACTIVE.value)
    avatar = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    address = Column(String(255), nullable=True)

    business_type = Column(String(50), nullable=True)
    company_name = Column(String(150), nullable=True)
    company_email = Column(String(100), nullable=True)
    company_phone = Column(String(20), nullable=True)
    legal_representative_name = Column(String(100), nullable=True)
    legal_representative_position = Column(String(100), nullable=True)
    legal_representative_id_number = Column(String(30), nullable=True)
    office_province = Column(String(100), nullable=True)
    office_district = Column(String(100), nullable=True)
    office_ward = Column(String(100), nullable=True)
    office_street = Column(String(255), nullable=True)
    shipping_same_as_office = Column(Boolean, default=True, nullable=False)
    shipping_province = Column(String(100), nullable=True)
    shipping_district = Column(String(100), nullable=True)
    shipping_ward = Column(String(100), nullable=True)
    shipping_street = Column(String(255), nullable=True)
    
    shop_name = Column(String(150), nullable=True)
    shop_description = Column(Text, nullable=True)
    business_license = Column(String(255), nullable=True) # Giấy phép kinh doanh / kiểm định sách thật
    seller_balance = Column(Float, default=0.0) # Số dư ví NXB sau khi trừ % sàn
    tax_code = Column(String(50), nullable=True)
    bank_name = Column(String(100), nullable=True)
    bank_account_number = Column(String(50), nullable=True)
    bank_account_holder = Column(String(100), nullable=True)
    warehouse_address = Column(String(255), nullable=True)
    shop_logo = Column(String(500), nullable=True)
    shop_banner = Column(String(500), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    rejected_by = Column(Integer, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    approved_by = Column(Integer, nullable=True)
    
    # Dành cho Độc giả VIP
    vip_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    books = relationship("Book", back_populates="seller", foreign_keys="Book.seller_id")
    orders = relationship("Order", back_populates="buyer", foreign_keys="Order.buyer_id")
    ads = relationship("AdCampaign", back_populates="seller")
    return_requests = relationship("ReturnRequest", back_populates="user", foreign_keys="ReturnRequest.user_id")
    reviews_written = relationship("Review", foreign_keys="Review.user_id", back_populates="user")
    reviews_received = relationship("Review", foreign_keys="Review.seller_id", back_populates="seller")

    @property
    def is_vip(self):
        if not self.vip_expires_at:
            return False
        return self.vip_expires_at > datetime.utcnow()

class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    icon = Column(String(50), default="book")
    description = Column(String(255), nullable=True)

    books = relationship("Book", back_populates="category")

class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    
    title = Column(String(255), index=True, nullable=False)
    author = Column(String(150), index=True, nullable=False)
    publisher = Column(String(150), nullable=True)
    price = Column(Float, nullable=False)
    discount_price = Column(Float, nullable=True)
    stock = Column(Integer, default=10, nullable=False)
    cover_image = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    book_format = Column(String(20), default="PAPER", nullable=False)
    cover_type = Column(String(20), default="SOFT", nullable=False)
    vip_eligible = Column(Boolean, default=False, nullable=False)
    isbn = Column(String(50), nullable=True)
    translator = Column(String(150), nullable=True)
    page_count = Column(Integer, nullable=True)
    publication_year = Column(Integer, nullable=True)
    language = Column(String(50), default="Tiếng Việt", nullable=True)
    preview_file_url = Column(String(500), nullable=True)
    
    # Đọc thử sách (Sample preview - vài trang đầu)
    sample_content = Column(Text, nullable=True)
    full_ebook_content = Column(Text, nullable=True) # Chỉ VIP mới xem được toàn bộ
    
    # Trạng thái duyệt của Admin, Tình trạng tồn kho NXB & Quảng cáo của NXB
    status = Column(String(20), default=BookStatus.PENDING.value)
    is_visible = Column(Boolean, default=True, nullable=False)
    is_out_of_stock = Column(Boolean, default=False, nullable=False)
    rejection_reason = Column(Text, nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    rejected_by = Column(Integer, nullable=True)
    is_featured_ad = Column(Boolean, default=False)
    ad_expires_at = Column(DateTime, nullable=True)
    
    sold_count = Column(Integer, default=0)
    rating = Column(Float, default=5.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    seller = relationship("User", back_populates="books", foreign_keys=[seller_id])
    category = relationship("Category", back_populates="books")
    order_items = relationship("OrderItem", back_populates="book")
    ad_campaigns = relationship("AdCampaign", back_populates="book")
    reviews = relationship("Review", back_populates="product", foreign_keys="Review.product_id")

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_code = Column(String(30), unique=True, index=True, nullable=False)
    buyer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Tài chính & % Phí sàn
    total_amount = Column(Float, nullable=False)
    platform_fee_percent = Column(Float, default=10.0) # Hoa hồng sàn 8-15% (mặc định 10%)
    platform_fee_amount = Column(Float, default=0.0)   # Tiền sàn thu về
    seller_payout_amount = Column(Float, default=0.0)  # Tiền NXB thực nhận
    
    # Vận chuyển & Thanh toán
    shipping_name = Column(String(100), nullable=False)
    shipping_phone = Column(String(20), nullable=False)
    shipping_address = Column(String(255), nullable=False)
    shipping_province = Column(String(100), nullable=True)
    shipping_province_code = Column(String(20), nullable=True)
    shipping_district = Column(String(100), nullable=True)
    shipping_district_code = Column(String(20), nullable=True)
    shipping_ward = Column(String(100), nullable=True)
    shipping_ward_code = Column(String(20), nullable=True)
    shipping_street = Column(String(255), nullable=True)
    shipping_method = Column(String(30), default="STANDARD")
    shipping_fee = Column(Float, default=30000.0)
    subtotal_amount = Column(Float, default=0.0)
    discount_amount = Column(Float, default=0.0)
    voucher_code = Column(String(50), nullable=True)
    terms_accepted = Column(Boolean, default=False, nullable=False)
    shipping_carrier = Column(String(100), default="Giao Hàng Nhanh (GHN Express)")
    tracking_number = Column(String(50), nullable=True)
    tracking_step = Column(Integer, default=1) # 1: Đã đặt, 2: Đã đóng gói, 3: Đang giao, 4: Đã nhận
    payment_method = Column(String(50), default="COD") # COD, VNPAY, MOMO, WALLET
    payment_status = Column(String(30), default=PaymentStatus.PENDING.value)
    
    status = Column(String(30), default=OrderStatus.PENDING.value)
    return_status = Column(String(30), default="NONE") # NONE, REQUESTED, APPROVED, REJECTED
    return_reason = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    buyer = relationship("User", back_populates="orders", foreign_keys=[buyer_id])
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    return_requests = relationship("ReturnRequest", back_populates="order", foreign_keys="ReturnRequest.order_id", cascade="all, delete-orphan")

class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    quantity = Column(Integer, default=1, nullable=False)
    price = Column(Float, nullable=False) # Giá tại thời điểm mua
    book_title = Column(String(255), nullable=True)
    book_cover = Column(String(500), nullable=True)

    order = relationship("Order", back_populates="items")
    book = relationship("Book", back_populates="order_items")
    seller = relationship("User", foreign_keys=[seller_id])
    return_items = relationship("ReturnRequestItem", back_populates="order_item", foreign_keys="ReturnRequestItem.order_item_id")
    reviews = relationship("Review", back_populates="order_item", foreign_keys="Review.order_item_id")

    @property
    def seller_shop_name(self):
        if self.seller and (self.seller.shop_name or self.seller.full_name):
            return self.seller.shop_name or self.seller.full_name
        if self.book and self.book.publisher:
            return self.book.publisher
        return "NXB Chính hãng"

    @property
    def publisher(self):
        if self.book and self.book.publisher:
            return self.book.publisher
        if self.seller and (self.seller.shop_name or self.seller.full_name):
            return self.seller.shop_name or self.seller.full_name
        return "NXB Chính hãng"

class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (UniqueConstraint("order_item_id", "user_id", name="uq_review_user_order_item"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    order_item_id = Column(Integer, ForeignKey("order_items.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("books.id"), nullable=False, index=True)
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    rating = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    status = Column(String(30), default=ReviewStatus.REVIEWED.value, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", foreign_keys=[user_id], back_populates="reviews_written")
    order = relationship("Order", foreign_keys=[order_id])
    order_item = relationship("OrderItem", foreign_keys=[order_item_id], back_populates="reviews")
    product = relationship("Book", foreign_keys=[product_id], back_populates="reviews")
    seller = relationship("User", foreign_keys=[seller_id], back_populates="reviews_received")
    images = relationship("ReviewImage", back_populates="review", cascade="all, delete-orphan")
    seller_reply = relationship("SellerReply", back_populates="review", uselist=False, cascade="all, delete-orphan")

class ReviewImage(Base):
    __tablename__ = "review_images"

    id = Column(Integer, primary_key=True, index=True)
    review_id = Column(Integer, ForeignKey("reviews.id"), nullable=False, index=True)
    image_url = Column(String(1000), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    review = relationship("Review", back_populates="images")

class SellerReply(Base):
    __tablename__ = "seller_replies"

    id = Column(Integer, primary_key=True, index=True)
    review_id = Column(Integer, ForeignKey("reviews.id"), nullable=False, unique=True, index=True)
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    review = relationship("Review", back_populates="seller_reply")
    seller = relationship("User", foreign_keys=[seller_id])

class ReturnRequest(Base):
    __tablename__ = "return_requests"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(30), default=ReturnRequestStatus.PENDING.value, nullable=False)
    reason = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    refund_method = Column(String(50), nullable=True)
    refund_amount = Column(Float, default=0.0, nullable=False)
    rejection_reason = Column(Text, nullable=True)
    admin_note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
    shipped_at = Column(DateTime, nullable=True)
    received_at = Column(DateTime, nullable=True)
    refunded_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)

    order = relationship("Order", back_populates="return_requests", foreign_keys=[order_id])
    user = relationship("User", back_populates="return_requests", foreign_keys=[user_id])
    items = relationship("ReturnRequestItem", back_populates="return_request", cascade="all, delete-orphan")

class ReturnRequestItem(Base):
    __tablename__ = "return_request_items"

    id = Column(Integer, primary_key=True, index=True)
    return_request_id = Column(Integer, ForeignKey("return_requests.id"), nullable=False)
    order_item_id = Column(Integer, ForeignKey("order_items.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    product_name = Column(String(255), nullable=True)

    return_request = relationship("ReturnRequest", back_populates="items")
    order_item = relationship("OrderItem", back_populates="return_items", foreign_keys=[order_item_id])
    product = relationship("Book", foreign_keys=[product_id])

class Address(Base):
    __tablename__ = "addresses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    recipient_name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False)
    province = Column(String(100), nullable=False)
    province_code = Column(String(20), nullable=True)
    district = Column(String(100), nullable=False)
    district_code = Column(String(20), nullable=True)
    ward = Column(String(100), nullable=False)
    ward_code = Column(String(20), nullable=True)
    street = Column(String(255), nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")

class Voucher(Base):
    __tablename__ = "vouchers"

    id = Column(Integer, primary_key=True, index=True)
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=True) # Null = Sàn, Not null = Shop Voucher
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(150), nullable=False)
    discount_type = Column(String(20), default="FIXED")
    discount_value = Column(Float, nullable=False)
    max_discount = Column(Float, nullable=True)
    min_order_amount = Column(Float, default=0.0)
    usage_limit = Column(Integer, nullable=True)
    used_count = Column(Integer, default=0, nullable=False)
    starts_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    seller = relationship("User")

class VoucherUsage(Base):
    __tablename__ = "voucher_usages"

    id = Column(Integer, primary_key=True, index=True)
    voucher_id = Column(Integer, ForeignKey("vouchers.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    used_at = Column(DateTime, default=datetime.utcnow)

    voucher = relationship("Voucher")

class VipSubscription(Base):
    __tablename__ = "vip_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan_name = Column(String(100), nullable=False) # VIP 1 Tháng, VIP 6 Tháng, VIP 1 Năm
    price = Column(Float, nullable=False)
    duration_days = Column(Integer, nullable=False)
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")

class AdCampaign(Base):
    __tablename__ = "ad_campaigns"

    id = Column(Integer, primary_key=True, index=True)
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    fee_paid = Column(Float, nullable=False)
    duration_days = Column(Integer, nullable=False)
    position = Column(String(50), default="HOME_TOP_BANNER")
    status = Column(String(30), default="ACTIVE")
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    seller = relationship("User", back_populates="ads")
    book = relationship("Book", back_populates="ad_campaigns")

class WithdrawalRequest(Base):
    __tablename__ = "withdrawal_requests"

    id = Column(Integer, primary_key=True, index=True)
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Float, nullable=False)
    bank_name = Column(String(100), nullable=False)
    bank_account_number = Column(String(50), nullable=False)
    bank_account_holder = Column(String(100), nullable=False)
    status = Column(String(30), default="PENDING") # PENDING, APPROVED, REJECTED
    note = Column(String(255), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    processed_at = Column(DateTime, nullable=True)
    transaction_id = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    seller = relationship("User")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    transaction_code = Column(String(50), unique=True, index=True, nullable=False)
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    payout_id = Column(Integer, ForeignKey("withdrawal_requests.id"), nullable=True)
    transaction_type = Column(String(30), nullable=False)
    gross_amount = Column(Float, default=0.0, nullable=False)
    fee_amount = Column(Float, default=0.0, nullable=False)
    net_amount = Column(Float, default=0.0, nullable=False)
    status = Column(String(30), default="PENDING", nullable=False)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Dispute(Base):
    __tablename__ = "disputes"

    id = Column(Integer, primary_key=True, index=True)
    dispute_code = Column(String(50), unique=True, index=True, nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    buyer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reason = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    amount = Column(Float, default=0.0, nullable=False)
    status = Column(String(30), default="OPEN", nullable=False)
    buyer_response = Column(Text, nullable=True)
    seller_response = Column(Text, nullable=True)
    admin_decision = Column(String(40), nullable=True)
    resolution_note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(Integer, nullable=True)


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    entity_type = Column(String(30), nullable=False)
    entity_id = Column(Integer, nullable=False)
    document_type = Column(String(40), nullable=False)
    file_name = Column(String(255), nullable=False)
    mime_type = Column(String(100), nullable=False)
    storage_path = Column(String(500), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(30), default="UPLOADED", nullable=False)

class SellerReviewAudit(Base):
    __tablename__ = "seller_review_audit"

    id = Column(Integer, primary_key=True, index=True)
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    admin_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(40), nullable=False)
    previous_status = Column(String(30), nullable=True)
    new_status = Column(String(30), nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    seller = relationship("User", foreign_keys=[seller_id])
    admin = relationship("User", foreign_keys=[admin_id])

class SellerStaff(Base):
    __tablename__ = "seller_staff"

    id = Column(Integer, primary_key=True, index=True)
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    staff_name = Column(String(100), nullable=False)
    staff_email = Column(String(100), nullable=False)
    staff_phone = Column(String(20), nullable=True)
    role = Column(String(30), default="WAREHOUSE") # WAREHOUSE, MARKETING, ACCOUNTANT
    status = Column(String(20), default="ACTIVE")
    created_at = Column(DateTime, default=datetime.utcnow)

    seller = relationship("User")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(50), nullable=False) # 'NEW_BOOK_SUBMITTED', 'BOOK_APPROVED', 'BOOK_REJECTED'
    reference_id = Column(Integer, nullable=True) # ID của cuốn sách liên quan
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", backref="notifications")



