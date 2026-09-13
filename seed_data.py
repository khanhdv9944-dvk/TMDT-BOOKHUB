import datetime
import sys
import io

# Đảm bảo in UTF-8 không bị lỗi trên Windows cmd/powershell
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from database import engine, SessionLocal, Base, migrate_schema

import models, auth

REFERENCE_CATALOG = [
    {"title": "Từ Sách Tâm Linh Thế Kỷ - Bốn Cấp Độ Chữa Lành", "author": "Nhiều tác giả", "publisher": "NXB Thế Giới", "price": 65000, "discount_price": 52000, "category": "ky-nang", "stock": 32, "sold_count": 122, "rating": 4.7, "cover_image": "https://images.unsplash.com/photo-1543002588-bfa74002ed7e?auto=format&fit=crop&q=80&w=500", "format": "PAPER"},
    {"title": "Vị Phật Ở Chung Nhà", "author": "Thích Nhất Hạnh", "publisher": "NXB Kim Đồng", "price": 128000, "discount_price": 104000, "category": "ky-nang", "stock": 28, "sold_count": 88, "rating": 4.8, "cover_image": "https://images.unsplash.com/photo-1507842217343-583bb7270b66?auto=format&fit=crop&q=80&w=500", "format": "PAPER"},
    {"title": "Chuẩn Bị Cho Bé Vào Lớp 1 - Luyện Viết Chữ Đ đẹp Tập 2", "author": "Ban biên soạn", "publisher": "NXB Giáo Dục", "price": 17000, "discount_price": 14000, "category": "thieu-nhi", "stock": 45, "sold_count": 210, "rating": 4.8, "cover_image": "https://images.unsplash.com/photo-1544717305-2782549b5136?auto=format&fit=crop&q=80&w=500", "format": "PAPER"},
    {"title": "Bạn Vẫn Bạn Mình - Hình Dung Hành Dung", "author": "Nhiều tác giả", "publisher": "NXB Trẻ", "price": 45000, "discount_price": 39000, "category": "ky-nang", "stock": 40, "sold_count": 122, "rating": 4.6, "cover_image": "https://images.unsplash.com/photo-1495446815901-a7297e633e8d?auto=format&fit=crop&q=80&w=500", "format": "PAPER"},
    {"title": "The Heroes Of Olympus 4: The House Of Hades", "author": "Rick Riordan", "publisher": "Disney Hyperion", "price": 348000, "discount_price": 284750, "category": "van-hoc", "stock": 18, "sold_count": 230, "rating": 4.9, "cover_image": "https://images.unsplash.com/photo-1516979187457-637abb4f9353?auto=format&fit=crop&q=80&w=500", "format": "PAPER", "cover_type": "HARD"},
    {"title": "Lịch Sử Triết Học Phương Đông Việt Cho Thanh Thiếu Niên", "author": "Nguyễn Hiền Trang", "publisher": "NXB Kim Đồng", "price": 139000, "discount_price": 119000, "category": "van-hoc", "stock": 22, "sold_count": 140, "rating": 4.8, "cover_image": "https://images.unsplash.com/photo-1526243741027-444d633d7365?auto=format&fit=crop&q=80&w=500", "format": "PAPER"},
    {"title": "Đứa Trẻ Cát", "author": "Tahar Ben Jelloun", "publisher": "NXB Hội Nhà Văn", "price": 170000, "discount_price": 126750, "category": "van-hoc", "stock": 25, "sold_count": 49, "rating": 4.6, "cover_image": "https://images.unsplash.com/photo-1519682337058-a94d519337bc?auto=format&fit=crop&q=80&w=500", "format": "PAPER"},
    {"title": "Truyện Ngụ Ngôn Thế Giới Chọn Lọc - Chú Ghé Xấu Hổ", "author": "Nhiều tác giả", "publisher": "NXB Kim Đồng", "price": 35000, "discount_price": 28000, "category": "thieu-nhi", "stock": 48, "sold_count": 129, "rating": 4.7, "cover_image": "https://images.unsplash.com/photo-1606092195730-5d7b9af1efc5?auto=format&fit=crop&q=80&w=500", "format": "PAPER"},
    {"title": "365 Bài Học Tâm Lý - Tập 3", "author": "Nhiều tác giả", "publisher": "NXB Phụ Nữ", "price": 120000, "discount_price": 60000, "category": "ky-nang", "stock": 30, "sold_count": 6, "rating": 4.5, "cover_image": "https://images.unsplash.com/photo-1516979187457-637abb4f9353?auto=format&fit=crop&q=80&w=500", "format": "PAPER"},
    {"title": "Tên Cô Ấy Là", "author": "Nhiều tác giả", "publisher": "NXB Trẻ", "price": 137000, "discount_price": 111000, "category": "van-hoc", "stock": 26, "sold_count": 39, "rating": 4.6, "cover_image": "https://images.unsplash.com/photo-1495446815901-a7297e633e8d?auto=format&fit=crop&q=80&w=500", "format": "PAPER"},
    {"title": "Đọc Sách Và Con Đường Gian Nan Vạn Dặm", "author": "Nhiều tác giả", "publisher": "NXB Hội Nhà Văn", "price": 109000, "discount_price": 83000, "category": "ky-nang", "stock": 31, "sold_count": 68, "rating": 4.7, "cover_image": "https://images.unsplash.com/photo-1497633762265-9d179a990aa6?auto=format&fit=crop&q=80&w=500", "format": "PAPER"},
    {"title": "Chế Độ Ăn Giảm Cân Và Kiểm Soát Đường Huyết", "author": "Nhiều tác giả", "publisher": "NXB Phụ Nữ", "price": 189000, "discount_price": 152000, "category": "ky-nang", "stock": 20, "sold_count": 319, "rating": 4.7, "cover_image": "https://images.unsplash.com/photo-1498837167922-ddd27525d352?auto=format&fit=crop&q=80&w=500", "format": "PAPER"},
    {"title": "You Are a Badass at Making Money", "author": "Jen Sincero", "publisher": "Viking", "price": 336000, "discount_price": 284750, "category": "kinh-te", "stock": 16, "sold_count": 133, "rating": 4.9, "cover_image": "https://images.unsplash.com/photo-1526243741027-444d633d7365?auto=format&fit=crop&q=80&w=500", "format": "PAPER"},
    {"title": "Combo Manga - Phiên Nữ Bé - Tập 5", "author": "Nhiều tác giả", "publisher": "NXB Kim Đồng", "price": 139000, "discount_price": 137500, "category": "thieu-nhi", "stock": 19, "sold_count": 254, "rating": 4.8, "cover_image": "https://images.unsplash.com/photo-1613376023733-0a73315d9b06?auto=format&fit=crop&q=80&w=500", "format": "PAPER"},
]

CONAN_COVER_IMAGES = {
    "Thám Tử Lừng Danh Conan - Tập 104 (Bản Đặc Biệt)": "/static/images/conan/conan-104.svg",
    "Thám Tử Lừng Danh Conan - Tập 103": "/static/images/conan/conan-103.svg",
    "Thám Tử Lừng Danh Conan - Tập 102": "/static/images/conan/conan-102.svg",
    "Thám Tử Lừng Danh Conan - Tập 107": "/static/images/conan/conan-107.svg",
    "Thám Tử Lừng Danh Conan - Tập 106": "/static/images/conan/conan-106.svg",
    "Thám Tử Lừng Danh Conan - Tập 31": "/static/images/conan/conan-31.svg",
    "Thám Tử Lừng Danh Conan - Tập 101": "/static/images/conan/conan-101.svg",
    "Thám Tử Lừng Danh Conan - Tập 105": "/static/images/conan/conan-105.svg",
    "Thám Tử Lừng Danh Conan - Tập 43": "/static/images/conan/conan-43.svg",
    "Thám Tử Lừng Danh Conan - Tập 33": "/static/images/conan/conan-33.svg",
    "Thám Tử Lừng Danh Conan - Tập 27": "/static/images/conan/conan-27.svg",
    "Thám Tử Lừng Danh Conan - Tập 15": "/static/images/conan/conan-15.svg",
}

ATTACHED_MANGA_CATALOG = [
    {"title": "Thám Tử Lừng Danh Conan - Tập 104 (Bản Đặc Biệt)", "author": "Gosho Aoyama", "publisher": "NXB Kim Đồng", "price": 23750, "discount_price": 21750, "category": "thieu-nhi", "stock": 66, "sold_count": 412, "rating": 4.9, "cover_image": CONAN_COVER_IMAGES["Thám Tử Lừng Danh Conan - Tập 104 (Bản Đặc Biệt)"], "format": "PAPER"},
    {"title": "Thám Tử Lừng Danh Conan - Tập 103", "author": "Gosho Aoyama", "publisher": "NXB Kim Đồng", "price": 23750, "discount_price": 21750, "category": "thieu-nhi", "stock": 62, "sold_count": 398, "rating": 4.9, "cover_image": CONAN_COVER_IMAGES["Thám Tử Lừng Danh Conan - Tập 103"], "format": "PAPER"},
    {"title": "Thám Tử Lừng Danh Conan - Tập 102", "author": "Gosho Aoyama", "publisher": "NXB Kim Đồng", "price": 24000, "discount_price": 22000, "category": "thieu-nhi", "stock": 58, "sold_count": 370, "rating": 4.9, "cover_image": CONAN_COVER_IMAGES["Thám Tử Lừng Danh Conan - Tập 102"], "format": "PAPER"},
    {"title": "Thám Tử Lừng Danh Conan - Tập 107", "author": "Gosho Aoyama", "publisher": "NXB Kim Đồng", "price": 23800, "discount_price": 21800, "category": "thieu-nhi", "stock": 50, "sold_count": 360, "rating": 4.9, "cover_image": CONAN_COVER_IMAGES["Thám Tử Lừng Danh Conan - Tập 107"], "format": "PAPER"},
    {"title": "Thám Tử Lừng Danh Conan - Tập 106", "author": "Gosho Aoyama", "publisher": "NXB Kim Đồng", "price": 23750, "discount_price": 21750, "category": "thieu-nhi", "stock": 54, "sold_count": 355, "rating": 4.9, "cover_image": CONAN_COVER_IMAGES["Thám Tử Lừng Danh Conan - Tập 106"], "format": "PAPER"},
    {"title": "Thám Tử Lừng Danh Conan - Tập 31", "author": "Gosho Aoyama", "publisher": "NXB Kim Đồng", "price": 33500, "discount_price": 30500, "category": "thieu-nhi", "stock": 41, "sold_count": 275, "rating": 4.8, "cover_image": CONAN_COVER_IMAGES["Thám Tử Lừng Danh Conan - Tập 31"], "format": "PAPER"},
    {"title": "Thám Tử Lừng Danh Conan - Tập 101", "author": "Gosho Aoyama", "publisher": "NXB Kim Đồng", "price": 24000, "discount_price": 22000, "category": "thieu-nhi", "stock": 48, "sold_count": 332, "rating": 4.9, "cover_image": CONAN_COVER_IMAGES["Thám Tử Lừng Danh Conan - Tập 101"], "format": "PAPER"},
    {"title": "Thám Tử Lừng Danh Conan - Tập 105", "author": "Gosho Aoyama", "publisher": "NXB Kim Đồng", "price": 23750, "discount_price": 21750, "category": "thieu-nhi", "stock": 52, "sold_count": 348, "rating": 4.9, "cover_image": CONAN_COVER_IMAGES["Thám Tử Lừng Danh Conan - Tập 105"], "format": "PAPER"},
    {"title": "Thám Tử Lừng Danh Conan - Tập 43", "author": "Gosho Aoyama", "publisher": "NXB Kim Đồng", "price": 33500, "discount_price": 30500, "category": "thieu-nhi", "stock": 38, "sold_count": 244, "rating": 4.8, "cover_image": CONAN_COVER_IMAGES["Thám Tử Lừng Danh Conan - Tập 43"], "format": "PAPER"},
    {"title": "Thám Tử Lừng Danh Conan - Tập 33", "author": "Gosho Aoyama", "publisher": "NXB Kim Đồng", "price": 33500, "discount_price": 30500, "category": "thieu-nhi", "stock": 42, "sold_count": 262, "rating": 4.8, "cover_image": CONAN_COVER_IMAGES["Thám Tử Lừng Danh Conan - Tập 33"], "format": "PAPER"},
    {"title": "Thám Tử Lừng Danh Conan - Tập 27", "author": "Gosho Aoyama", "publisher": "NXB Kim Đồng", "price": 33500, "discount_price": 30500, "category": "thieu-nhi", "stock": 36, "sold_count": 231, "rating": 4.8, "cover_image": CONAN_COVER_IMAGES["Thám Tử Lừng Danh Conan - Tập 27"], "format": "PAPER"},
    {"title": "Thám Tử Lừng Danh Conan - Tập 15", "author": "Gosho Aoyama", "publisher": "NXB Kim Đồng", "price": 24000, "discount_price": 22000, "category": "thieu-nhi", "stock": 46, "sold_count": 302, "rating": 4.8, "cover_image": CONAN_COVER_IMAGES["Thám Tử Lừng Danh Conan - Tập 15"], "format": "PAPER"}
]

NON_BOOK_TITLES = {
    "Lồng Đèn Trung Thu Gỗ Mộc Mẫu",
    "Siêu Xe Hot Wheels C4982 - HW50 Concept",
    "Đồ Chơi Lắp Ráp Lego Classic 10696",
    "Xe Tải Nhiều Ngăn - Cảnh Sát Nhí VECTO 666-02K",
    "Hộp 80 Bút Marker Acrylic FIZZ",
}

EXTRA_CATEGORIES = [
    ("Văn Học", "van-hoc-mo-rong", "feather"),
    ("Lịch Sử", "lich-su", "history"),
    ("Giáo Dục", "giao-duc", "book-open"),
    ("Ngoại Ngữ", "ngoai-ngu", "languages"),
    ("Tâm Lý & Kỹ Năng Sống", "tam-ly-ky-nang", "brain"),
    ("Thiếu Nhi", "thieu-nhi-mo-rong", "smile"),
    ("Tôn Giáo & Tâm Linh", "ton-giao-tam-linh", "compass"),
    ("Khoa Học & Công Nghệ", "khoa-hoc-cong-nghe", "cpu"),
]

FIXED_COVER_URLS = {
    "Disney Frozen 2 (Happier Tin)": "https://images.unsplash.com/photo-1543002588-bfa74002ed7e?auto=format&fit=crop&q=80&w=500",
    "The Heroes Of Olympus 4: The House Of Hades": "https://images.unsplash.com/photo-1516979187457-637abb4f9353?auto=format&fit=crop&q=80&w=500",
    "Tên Cô Ấy Là": "https://images.unsplash.com/photo-1495446815901-a7297e633e8d?auto=format&fit=crop&q=80&w=500",
    "You Are a Badass at Making Money": "https://images.unsplash.com/photo-1526243741027-444d633d7365?auto=format&fit=crop&q=80&w=500",
    "Thám Tử Lừng Danh Conan - Tập 104 (Bản Đặc Biệt)": "/static/images/conan/conan-104.svg",
    "Thám Tử Lừng Danh Conan - Tập 103": "/static/images/conan/conan-103.svg",
    "Thám Tử Lừng Danh Conan - Tập 102": "/static/images/conan/conan-102.svg",
    "Thám Tử Lừng Danh Conan - Tập 107": "/static/images/conan/conan-107.svg",
    "Thám Tử Lừng Danh Conan - Tập 106": "/static/images/conan/conan-106.svg",
    "Thám Tử Lừng Danh Conan - Tập 31": "/static/images/conan/conan-31.svg",
    "Thám Tử Lừng Danh Conan - Tập 101": "/static/images/conan/conan-101.svg",
    "Thám Tử Lừng Danh Conan - Tập 105": "/static/images/conan/conan-105.svg",
    "Thám Tử Lừng Danh Conan - Tập 43": "/static/images/conan/conan-43.svg",
    "Thám Tử Lừng Danh Conan - Tập 33": "/static/images/conan/conan-33.svg",
    "Thám Tử Lừng Danh Conan - Tập 27": "/static/images/conan/conan-27.svg",
    "Thám Tử Lừng Danh Conan - Tập 15": "/static/images/conan/conan-15.svg",
}

def sync_reference_catalog(db):
    """Add the requested marketplace catalog without duplicating existing titles."""
    db.query(models.Book).filter(models.Book.title.in_(NON_BOOK_TITLES)).delete(synchronize_session=False)
    db.flush()
    existing_category_slugs = {category.slug for category in db.query(models.Category).all()}
    for name, slug, icon in EXTRA_CATEGORIES:
        if slug not in existing_category_slugs:
            db.add(models.Category(name=name, slug=slug, icon=icon, description=f"Danh mục {name}"))
    db.flush()
    for title, cover_url in FIXED_COVER_URLS.items():
        db.query(models.Book).filter(models.Book.title == title).update({"cover_image": cover_url}, synchronize_session=False)
    sellers = {user.username: user for user in db.query(models.User).filter(models.User.role == models.UserRole.SELLER.value).all()}
    categories = {category.slug: category for category in db.query(models.Category).all()}
    existing = {book.title for book in db.query(models.Book).all()}
    seller = sellers.get("nxb_kimdong") or next(iter(sellers.values()), None)
    if not seller:
        return 0
    added = 0
    all_catalog_items = REFERENCE_CATALOG + ATTACHED_MANGA_CATALOG
    for item in all_catalog_items:
        if item["title"] in existing or item["category"] not in categories:
            continue
        db.add(models.Book(
            seller_id=seller.id,
            category_id=categories[item["category"]].id,
            title=item["title"],
            author=item["author"],
            publisher=item["publisher"],
            price=item["price"],
            discount_price=item["discount_price"],
            stock=item["stock"],
            sold_count=item["sold_count"],
            rating=item["rating"],
            cover_image=item["cover_image"],
            description=f"Sản phẩm {item['title']} được bổ sung vào catalog BookHub.",
            status=models.BookStatus.APPROVED.value,
            book_format=item.get("format", "PAPER"),
            cover_type=item.get("cover_type", "SOFT"),
            vip_eligible=item.get("format") == "EBOOK",
        ))
        added += 1
    return added

def sync_sample_notifications(db):
    """Đảm bảo NXB có các thông báo mẫu về đơn hàng và hệ thống nếu chưa có."""
    nhanam = db.query(models.User).filter(models.User.username == "nxb_nhanam").first()
    if not nhanam:
        return
    
    existing_count = db.query(models.Notification).filter(models.Notification.user_id == nhanam.id).count()
    if existing_count == 0:
        order = db.query(models.Order).first()
        order_code = order.order_code if order else "BH-260824-A182C3"
        order_id = order.id if order else 1
        book = db.query(models.Book).filter(models.Book.seller_id == nhanam.id).first()
        book_id = book.id if book else 1
        book_title = book.title if book else "Bốn Cấp Độ Chữa Lành"
        
        now_utc = datetime.datetime.utcnow()
        notifs = [
            models.Notification(
                user_id=nhanam.id,
                title="Đơn hàng mới từ khách hàng",
                message=f"Bạn có đơn hàng mới #{order_code} từ khách hàng Nguyễn Văn An (Tổng tiền: 214.000 đ). Vui lòng chuẩn bị đóng gói.",
                type=models.NotificationType.ORDER_CREATED.value,
                reference_id=order_id,
                is_read=False,
                created_at=now_utc - datetime.timedelta(minutes=15)
            ),
            models.Notification(
                user_id=nhanam.id,
                title="Khách hàng đã nhận hàng thành công",
                message=f"Khách hàng Trần Minh Thư đã xác nhận nhận thành công đơn hàng #{order_code}. Doanh thu 192.600 đ đã cộng vào số dư ví.",
                type=models.NotificationType.ORDER_DELIVERED.value,
                reference_id=order_id,
                is_read=False,
                created_at=now_utc - datetime.timedelta(hours=2)
            ),
            models.Notification(
                user_id=nhanam.id,
                title="Cảnh báo tồn kho thấp",
                message=f"Cuốn sách '{book_title}' trong kho của bạn chỉ còn tồn kho 4 cuốn (ngưỡng an toàn: 5 cuốn). Hãy bổ sung thêm hàng.",
                type=models.NotificationType.LOW_STOCK_ALERT.value,
                reference_id=book_id,
                is_read=False,
                created_at=now_utc - datetime.timedelta(hours=5)
            ),
            models.Notification(
                user_id=nhanam.id,
                title="Đánh giá 5 sao từ khách hàng",
                message=f"Khách hàng Trần Minh Thư vừa đánh giá ⭐⭐⭐⭐⭐ cho đơn #{order_code}: 'Sách đóng gói cực kỳ cẩn thận, bìa cứng cáp và giao hàng siêu nhanh!'",
                type=models.NotificationType.ORDER_REVIEWED.value,
                reference_id=order_id,
                is_read=True,
                created_at=now_utc - datetime.timedelta(hours=8)
            ),
            models.Notification(
                user_id=nhanam.id,
                title="Sách đã được phê duyệt",
                message=f"Cuốn sách '{book_title}' của bạn đã được Admin duyệt và chính thức mở bán trên sàn BookHub!",
                type=models.NotificationType.BOOK_APPROVED.value,
                reference_id=book_id,
                is_read=True,
                created_at=now_utc - datetime.timedelta(days=1)
            ),
            models.Notification(
                user_id=nhanam.id,
                title="Thông báo từ Ban Quản Trị BookHub",
                message="BookHub triển khai chương trình 'Tháng Vàng Tri Ân Độc Giả' - Trợ giá 50% phí vận chuyển toàn quốc cho các gian hàng NXB chính hãng.",
                type=models.NotificationType.SYSTEM_ANNOUNCEMENT.value,
                reference_id=None,
                is_read=False,
                created_at=now_utc - datetime.timedelta(hours=12)
            ),
        ]
        db.add_all(notifs)
        db.commit()

def seed_database():
    # Tạo tất cả các bảng nếu chưa có
    Base.metadata.create_all(bind=engine)
    migrate_schema()
    
    db = SessionLocal()
    try:
        if not db.query(models.Voucher).first():
            db.add_all([
                models.Voucher(code="BOOKHUB20", name="Giảm 20.000đ cho đơn từ 100.000đ", discount_type="FIXED", discount_value=20000, min_order_amount=100000, usage_limit=1000),
                models.Voucher(code="BOOKHUB10", name="Giảm 10% tối đa 50.000đ", discount_type="PERCENT", discount_value=10, max_discount=50000, min_order_amount=150000, usage_limit=1000),
            ])
            db.commit()

        # Kiểm tra nếu đã có dữ liệu thì không seed lại
        if db.query(models.User).first():
            added = sync_reference_catalog(db)
            sync_sample_notifications(db)
            db.commit()
            print("Cơ sở dữ liệu đã tồn tại dữ liệu!")
            if added:
                print(f"Đã bổ sung {added} sản phẩm tham chiếu vào catalog.")
            return

        print("Đang khởi tạo dữ liệu mẫu cho Sàn TMĐT Sách...")

        # 1. TẠO TÀI KHOẢN MẪU (3 CÁNH CỬA)
        # ----------------------------------------------------
        admin_user = models.User(
            username="admin",
            email="admin@bookhub.vn",
            hashed_password=auth.get_password_hash("123456"),
            full_name="Nguyễn Văn Sàn (Admin Chủ Sàn)",
            role=models.UserRole.ADMIN.value,
            status=models.UserStatus.ACTIVE.value,
            avatar="https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&q=80&w=200",
            phone="0901234567"
        )
        db.add(admin_user)

        # NXB Kim Đồng (Đã duyệt uy tín)
        nxb_kd = models.User(
            username="nxb_kimdong",
            email="contact@nxbkimdong.com.vn",
            hashed_password=auth.get_password_hash("123456"),
            full_name="Nhà Xuất Bản Kim Đồng",
            shop_name="NXB Kim Đồng Official Store",
            shop_description="NXB uy tín hàng đầu Việt Nam về sách thiếu nhi, văn học tuổi trẻ, manga bản quyền 100%.",
            business_license="GPKD-KD-2024-8899 (Đã kiểm định sách chính hãng)",
            role=models.UserRole.SELLER.value,
            status=models.UserStatus.ACTIVE.value,
            avatar="https://images.unsplash.com/photo-1568602471122-7832951cc4c5?auto=format&fit=crop&q=80&w=200",
            phone="02439434730",
            address="55 Quang Trung, Hai Bà Trưng, Hà Nội",
            seller_balance=2450000.0
        )
        db.add(nxb_kd)

        # NXB Nhã Nam (Đã duyệt uy tín)
        nxb_nhanam = models.User(
            username="nxb_nhanam",
            email="info@nhanam.vn",
            hashed_password=auth.get_password_hash("123456"),
            full_name="Công ty CP Sách Nhã Nam",
            shop_name="Nhã Nam Book Store",
            shop_description="Bởi vì sách là thế giới. Nơi hội tụ tinh hoa văn học thế giới và sách tư duy kinh điển.",
            business_license="GPKD-NN-2023-7712 (Chứng nhận bản quyền xuất bản)",
            role=models.UserRole.SELLER.value,
            status=models.UserStatus.ACTIVE.value,
            avatar="https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?auto=format&fit=crop&q=80&w=200",
            phone="02435146875",
            address="59 Đỗ Quang, Trung Hòa, Cầu Giấy, Hà Nội",
            seller_balance=4120000.0
        )
        db.add(nxb_nhanam)

        # Tiệm Sách Hải Đăng (Chờ Admin duyệt - Chống sách giả)
        tiem_haidang = models.User(
            username="tiemsach_haidang",
            email="haidangbook@gmail.com",
            hashed_password=auth.get_password_hash("123456"),
            full_name="Tiệm Sách Cũ & Mới Hải Đăng",
            shop_name="Hải Đăng Bookstore",
            shop_description="Chuyên phân phối sách giảm giá, sách hiếm, giáo trình đại học toàn quốc.",
            business_license="Đang nộp hồ sơ GPKD số HD-99812",
            role=models.UserRole.SELLER.value,
            status=models.UserStatus.PENDING_SELLER_APPROVAL.value, # Chờ Admin duyệt
            avatar="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&q=80&w=200",
            phone="0987654321",
            address="120 Trần Đại Nghĩa, Hai Bà Trưng, Hà Nội"
        )
        db.add(tiem_haidang)

        # Độc giả thường
        buyer1 = models.User(
            username="docgia_an",
            email="an.nguyen@gmail.com",
            hashed_password=auth.get_password_hash("123456"),
            full_name="Nguyễn Bình An",
            role=models.UserRole.BUYER.value,
            status=models.UserStatus.ACTIVE.value,
            avatar="https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&q=80&w=200",
            phone="0912348899",
            address="Toà nhà Landmark 81, P.22, Bình Thạnh, TP.HCM"
        )
        db.add(buyer1)

        # Độc giả VIP (Gói năm)
        buyer_vip = models.User(
            username="docgia_vip",
            email="minh.thu@gmail.com",
            hashed_password=auth.get_password_hash("123456"),
            full_name="Trần Minh Thư (Hội viên VIP)",
            role=models.UserRole.BUYER.value,
            status=models.UserStatus.ACTIVE.value,
            avatar="https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&q=80&w=200",
            phone="0934567890",
            address="128 Nguyễn Trãi, Quận 1, TP.HCM",
            vip_expires_at=datetime.datetime.utcnow() + datetime.timedelta(days=300)
        )
        db.add(buyer_vip)

        # Tài khoản vi phạm bị khóa (Demo chống gian lận)
        banned_user = models.User(
            username="seller_fakebooks",
            email="fakebooks@darkweb.com",
            hashed_password=auth.get_password_hash("123456"),
            full_name="Tiệm Sách Lậu Sài Gòn",
            shop_name="Kho Sách Photo Giá Rẻ",
            role=models.UserRole.SELLER.value,
            status=models.UserStatus.BANNED.value, # Bị khóa
            avatar="https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&q=80&w=200",
            phone="0999999999"
        )
        db.add(banned_user)

        db.flush()

        # 2. TẠO DANH MỤC SÁCH
        # ----------------------------------------------------
        cat_kinhte = models.Category(name="Kinh Tế & Khởi Nghiệp", slug="kinh-te", icon="trending-up", description="Sách tư duy làm giàu, tài chính cá nhân, quản trị kinh doanh")
        cat_vanhoc = models.Category(name="Văn Học & Tiểu Thuyết", slug="van-hoc", icon="feather", description="Tác phẩm văn học kinh điển, tiểu thuyết đương đại")
        cat_kynang = models.Category(name="Kỹ Năng & Phát Triển Bản Thân", slug="ky-nang", icon="zap", description="Phát triển tư duy, giao tiếp, tâm lý học ứng dụng")
        cat_congnghe = models.Category(name="Công Nghệ & Lập Trình AI", slug="cong-nghe", icon="cpu", description="Sách khoa học máy tính, trí tuệ nhân tạo, thiết kế hệ thống")
        cat_thieunhi = models.Category(name="Thiếu Nhi & Manga", slug="thieu-nhi", icon="smile", description="Truyện tranh manga bản quyền, sách bồi dưỡng tâm hồn trẻ thơ")

        db.add_all([cat_kinhte, cat_vanhoc, cat_kynang, cat_congnghe, cat_thieunhi])
        db.flush()

        # 3. TẠO DANH SÁCH SÁCH & NỘI DUNG ĐỌC THỬ
        # ----------------------------------------------------
        books_data = [
            # Sách 1: Nhã Nam (Có mua Quảng Cáo Ghim Top Trang Chủ)
            models.Book(
                seller_id=nxb_nhanam.id,
                category_id=cat_vanhoc.id,
                title="Nhà Giả Kim (The Alchemist)",
                author="Paulo Coelho",
                publisher="NXB Hội Nhà Văn / Nhã Nam",
                price=89000,
                discount_price=75000,
                stock=45,
                cover_image="https://images.unsplash.com/photo-1544947950-fa07a98d237f?auto=format&fit=crop&q=80&w=500",
                description="Tất cả những trải nghiệm trong chuyến phiêu lưu theo đuổi vận mệnh của chàng chăn cừu Santiago đã giúp cậu thấu hiểu được ý nghĩa sâu xa nhất của hạnh phúc, hòa hợp với vũ trụ và con người.",
                sample_content="""CHƯƠNG 1: DƯỚI BÓNG CÂY VẢ HOANG
Cậu bé tên là Santiago. Trời vừa sẩm tối khi cậu cùng đàn cừu đến một nhà thờ cổ hoang phế. Mái nhà thờ đã sụp từ lâu và một cây vả to tướng đã mọc lên ngay nơi trước kia là phòng thánh.
Cậu quyết định nghỉ đêm tại đây. Cậu lùa đàn cừu qua khung cửa đã mục nát rồi dùng mấy thanh gỗ chặn lại để không con nào đi lạc lúc nửa đêm. Vùng này không có chó sói, nhưng đêm trước một con cừu đã trốn mất khiến cậu mất cả ngày hôm sau mới tìm ra.

Cậu trải chiếc áo khoác trên nền đất phủ đầy cỏ rồi gối đầu lên cuốn sách vừa đọc xong. Trước khi ngủ, cậu tự nhủ phải kiếm những cuốn sách dày hơn để đọc được lâu hơn và làm gối cũng êm hơn...""",
                full_ebook_content="""TOÀN BỘ BẢN EBOOK BẢN QUYỀN (DÀNH CHO HỘI VIÊN VIP)
...Chàng trai tiếp tục hành trình vượt qua sa mạc Sahara huyền bí.
'Khi bạn thực sự khao khát một điều gì, toàn bộ vũ trụ sẽ hợp sức lại giúp bạn đạt được điều đó.' - Nhà Giả Kim mỉm cười nói với Santiago khi ngắm nhìn ánh hoàng hôn đỏ rực buông xuống những đụn cát ngút ngàn.
Hành trình khám phá kho báu thực chất chính là hành trình tìm lại bản ngã và tiếng nói của trái tim mình...""",
                status=models.BookStatus.APPROVED.value,
                is_featured_ad=True, # ĐÃ MUA QUẢNG CÁO TOP BANNER
                sold_count=320,
                rating=4.9
            ),
            # Sách 2: NXB Kim Đồng (Quảng Cáo Top)
            models.Book(
                seller_id=nxb_kd.id,
                category_id=cat_thieunhi.id,
                title="Doraemon - Tuyển Tập Tranh Truyện Màu (Tập 1)",
                author="Fujiko F Fujio",
                publisher="NXB Kim Đồng",
                price=55000,
                discount_price=48000,
                stock=120,
                cover_image="https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?auto=format&fit=crop&q=80&w=500",
                description="Bộ truyện tranh thiếu nhi kinh điển gắn liền với tuổi thơ nhiều thế hệ độc giả. Phiên bản in màu sắc nét, giấy mỹ thuật cao cấp.",
                sample_content="""HỒI 1: CHÚ MÈO MÁY ĐẾN TỪ TƯƠNG LAI
Vào một buổi chiều êm ả ngày mùng một Tết, Nobita đang nằm dài lười biếng trên chiếu tatami trong phòng ngủ. Bỗng nhiên, từ ngăn kéo bàn học phát ra những tiếng lục cục kỳ lạ.
'Ủa? Cái ngăn kéo đang rung lên kìa!' - Nobita giật thót tim.
Kéttttt... Ngăn kéo từ từ mở ra, và một chú mèo máy màu xanh tròn trịa, không có tai, cùng một cậu bé kỳ lạ chui ra!
'Xin chào Nobita! Tớ là Doraemon, đến từ thế kỷ 22!'""",
                full_ebook_content="""TOÀN BỘ EBOOK TRANH TRUYỆN MÀU BẢN QUYỀN VIP
...Nobita mở rộng túi thần kỳ và bay lượn trên bầu trời Tokyo bằng Chong chóng tre. Những chuyến phiêu lưu kỳ thú cùng Shizuka, Jaian, Suneo bắt đầu mở ra vô vàn bài học về tình bạn và lòng dũng cảm!""",
                status=models.BookStatus.APPROVED.value,
                is_featured_ad=True, # ĐÃ MUA QUẢNG CÁO
                sold_count=510,
                rating=5.0
            ),
            # Sách 3: Nhã Nam - Kinh Tế
            models.Book(
                seller_id=nxb_nhanam.id,
                category_id=cat_kinhte.id,
                title="Tâm Lý Học Về Tiền (Psychology of Money)",
                author="Morgan Housel",
                publisher="NXB Dân Trí / Nhã Nam",
                price=169000,
                discount_price=139000,
                stock=80,
                cover_image="https://images.unsplash.com/photo-1592496431122-2349e0fbc666?auto=format&fit=crop&q=80&w=500",
                description="19 câu chuyện ngắn khai phá những thiên kiến tâm lý, cách con người đối xử với tiền bạc, sự giàu có và hạnh phúc tài chính bền vững.",
                sample_content="""CHƯƠNG 1: KHÔNG AI ĐIÊN CẢ
Kinh nghiệm cá nhân của bạn về tiền bạc chỉ chiếm khoảng 0.00000001% những gì xảy ra trên thế giới, nhưng lại quyết định tới 80% cách bạn nghĩ thế giới vận hành.
Một người lớn lên trong thời kỳ Đại suy thoái sẽ nhìn nhận rủi ro thị trường chứng khoán hoàn toàn khác với một người bước vào độ tuổi lao động trong cơn sốt cổ phiếu công nghệ thập niên 1990...""",
                full_ebook_content="""TOÀN BỘ EBOOK VIP: TÂM LÝ HỌC VỀ TIỀN
...Sự giàu có thực sự là những gì bạn không nhìn thấy. Đó là những chiếc xe chưa mua, những chiếc đồng hồ kim cương chưa đeo, và sự tự do thức dậy mỗi sáng quyết định làm những điều mình thích!""",
                status=models.BookStatus.APPROVED.value,
                is_featured_ad=False,
                sold_count=215,
                rating=4.8
            ),
            # Sách 4: Kỹ năng
            models.Book(
                seller_id=nxb_nhanam.id,
                category_id=cat_kynang.id,
                title="Atomic Habits - Thay Đổi Tí Hon, Hiệu Quả Bất Ngờ",
                author="James Clear",
                publisher="NXB Thế Giới",
                price=189000,
                discount_price=155000,
                stock=60,
                cover_image="https://images.unsplash.com/photo-1512820790803-83ca734da794?auto=format&fit=crop&q=80&w=500",
                description="Bí quyết xây dựng thói quen tốt và loại bỏ thói quen xấu mỗi ngày chỉ với 1% tiến bộ đều đặn.",
                sample_content="""CHƯƠNG 1: SỨC MẠNH BẤT NGỜ CỦA 1% MỖI NGÀY
Thật dễ để đánh giá quá cao tầm quan trọng của một khoảnh khắc định hình và đánh giá thấp giá trị của việc tạo ra những cải thiện nhỏ mỗi ngày.
Nếu bạn có thể trở nên tốt hơn 1% mỗi ngày trong vòng một năm, bạn sẽ kết thúc năm đó với kết quả tốt hơn gấp 37 lần...""",
                full_ebook_content="""TOÀN BỘ EBOOK VIP: ATOMIC HABITS
...4 Quy luật thay đổi hành vi: 1. Làm cho nó rõ ràng; 2. Làm cho nó hấp dẫn; 3. Làm cho nó dễ dàng; 4. Làm cho nó thỏa mãn!""",
                status=models.BookStatus.APPROVED.value,
                is_featured_ad=False,
                sold_count=430,
                rating=4.9
            ),
            # Sách 5: Công nghệ & AI
            models.Book(
                seller_id=nxb_nhanam.id,
                category_id=cat_congnghe.id,
                title="Cuộc Cách Mạng AI & Trí Tuệ Nhân Tạo 2026",
                author="Kai-Fu Lee",
                publisher="NXB Tổng Hợp",
                price=220000,
                discount_price=185000,
                stock=35,
                cover_image="https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&q=80&w=500",
                description="Bức tranh toàn cảnh về cách các mô hình ngôn ngữ lớn (LLM), robot tự hành và AI đại chúng đang tái cấu trúc nền kinh tế số.",
                sample_content="""MỞ ĐẦU: LÀN SÓNG THỨ TƯ CỦA NHÂN LOẠI
Chúng ta không còn nói về viễn cảnh tương lai xa xôi. Ngay lúc này, các siêu hệ thống AI đã có thể lập trình, phân tích y khoa và sáng tạo nội dung ở tốc độ gấp hàng ngàn lần con người...""",
                full_ebook_content="""TOÀN BỘ EBOOK VIP: CUỘC CÁCH MẠNG AI 2026...""",
                status=models.BookStatus.APPROVED.value,
                is_featured_ad=False,
                sold_count=98,
                rating=4.7
            ),
            # Sách 6: Sách NXB Kim Đồng
            models.Book(
                seller_id=nxb_kd.id,
                category_id=cat_vanhoc.id,
                title="Dế Mèn Phiêu Lưu Ký",
                author="Tô Hoài",
                publisher="NXB Kim Đồng",
                price=65000,
                discount_price=52000,
                stock=90,
                cover_image="https://images.unsplash.com/photo-1543002588-bfa74002ed7e?auto=format&fit=crop&q=80&w=500",
                description="Tác phẩm văn học thiếu nhi bất hủ ca ngợi tình bạn, lòng nhân ái và khát vọng sống tự do, hòa bình.",
                sample_content="""BÀI HỌC ĐƯỜNG ĐỜI ĐẦU TIÊN
Tôi sống độc lập từ thuở bé. Ấy là tục lệ lâu đời trong họ nhà dế chúng tôi. Mẹ tôi bảo: 'Cứ sinh ra được ít lâu, biết kiếm ăn là phải tự lập.'
Tôi rất tự hào vì đôi càng tôi mẫm bóng, vuốt ở chân cứ cứng dần và nhọn hoắt...""",
                full_ebook_content="""TOÀN BỘ EBOOK VIP: DẾ MÈN PHIÊU LƯU KÝ...""",
                status=models.BookStatus.APPROVED.value,
                is_featured_ad=False,
                sold_count=180,
                rating=4.9
            ),
            # Sách 7: Sách MỚI ĐĂNG - Chờ Admin DUYỆT (Demo Cửa Admin)
            models.Book(
                seller_id=nxb_kd.id,
                category_id=cat_thieunhi.id,
                title="Thám Tử Lừng Danh Conan - Tập 104 (Bản Đặc Biệt)",
                author="Gosho Aoyama",
                publisher="NXB Kim Đồng",
                price=70000,
                discount_price=60000,
                stock=50,
                cover_image="https://images.unsplash.com/photo-1589829085413-56de8ae18c73?auto=format&fit=crop&q=80&w=500",
                description="Tập truyện mới nhất vừa cập bến với những vụ án bí ẩn nghẹt thở và màn chạm trán Tổ chức Áo đen.",
                sample_content="""VỤ ÁN TRONG KHÁCH SẠN BÍ MẬT... Chờ Admin duyệt để hiển thị công khai!""",
                full_ebook_content="""Bản Ebook Conan 104...""",
                status=models.BookStatus.PENDING.value, # CHỜ ADMIN DUYỆT
                is_featured_ad=False,
                sold_count=0,
                rating=5.0
            ),
            # Sách 8: Sách Chờ Duyệt 2
            models.Book(
                seller_id=nxb_nhanam.id,
                category_id=cat_kinhte.id,
                title="Khởi Nghiệp Tinh Gọn (The Lean Startup)",
                author="Eric Ries",
                publisher="NXB Trẻ / Nhã Nam",
                price=145000,
                discount_price=120000,
                stock=40,
                cover_image="https://images.unsplash.com/photo-1516979187457-637abb4f9353?auto=format&fit=crop&q=80&w=500",
                description="Phương pháp xây dựng doanh nghiệp thành công bằng cách liên tục kiểm chứng giả thuyết và tối ưu vòng lặp Build-Measure-Learn.",
                sample_content="""Vòng lặp Phản hồi Xây dựng - Đo lường - Học hỏi...""",
                full_ebook_content="""Toàn bộ Lean Startup...""",
                status=models.BookStatus.PENDING.value, # CHỜ ADMIN DUYỆT
                is_featured_ad=False,
                sold_count=0,
                rating=4.8
            )
        ]

        db.add_all(books_data)
        db.flush()

        # 4. TẠO CHIẾN DỊCH QUẢNG CÁO MẪU (Doanh thu Ads cho Admin)
        # ----------------------------------------------------
        ad1 = models.AdCampaign(
            seller_id=nxb_nhanam.id,
            book_id=books_data[0].id, # Nhà Giả Kim
            fee_paid=500000.0, # 500k tiền quảng cáo
            duration_days=30,
            start_date=datetime.datetime.utcnow() - datetime.timedelta(days=5),
            end_date=datetime.datetime.utcnow() + datetime.timedelta(days=25),
            status="ACTIVE"
        )
        ad2 = models.AdCampaign(
            seller_id=nxb_kd.id,
            book_id=books_data[1].id, # Doraemon
            fee_paid=800000.0, # 800k tiền quảng cáo
            duration_days=30,
            start_date=datetime.datetime.utcnow() - datetime.timedelta(days=2),
            end_date=datetime.datetime.utcnow() + datetime.timedelta(days=28),
            status="ACTIVE"
        )
        db.add_all([ad1, ad2])

        # 5. TẠO GÓI VIP MẪU (Doanh thu VIP cho Admin)
        # ----------------------------------------------------
        vip1 = models.VipSubscription(
            user_id=buyer_vip.id,
            plan_name="Gói VIP Hoàng Gia (1 Năm)",
            price=449000.0,
            duration_days=365,
            start_date=datetime.datetime.utcnow() - datetime.timedelta(days=10),
            end_date=datetime.datetime.utcnow() + datetime.timedelta(days=355)
        )
        db.add(vip1)

        # 6. TẠO ĐƠN HÀNG MẪU (Doanh thu Bán sách & Hoa hồng Sàn 5%)
        # ----------------------------------------------------
        # Đơn 1: Đang đóng gói
        order1 = models.Order(
            order_code="BH-260824-A189C2",
            buyer_id=buyer1.id,
            total_amount=214000.0,
            platform_fee_percent=5.0,
            platform_fee_amount=10700.0, # Sàn thu 10.7k
            seller_payout_amount=192600.0, # NXB nhận 192.6k
            shipping_name="Nguyễn Bình An",
            shipping_phone="0912348899",
            shipping_address="Toà nhà Landmark 81, P.22, Bình Thạnh, TP.HCM",
            shipping_carrier="Giao Hàng Nhanh (GHN)",
            payment_method="COD",
            status=models.OrderStatus.PACKING.value, # NXB đã bấm Xác nhận đóng gói
            tracking_step=2,
            created_at=datetime.datetime.utcnow() - datetime.timedelta(hours=6)
        )
        db.add(order1)
        db.flush()

        item1_1 = models.OrderItem(
            order_id=order1.id,
            book_id=books_data[0].id,
            seller_id=nxb_nhanam.id,
            quantity=1,
            price=75000.0,
            book_title=books_data[0].title,
            book_cover=books_data[0].cover_image
        )
        item1_2 = models.OrderItem(
            order_id=order1.id,
            book_id=books_data[2].id,
            seller_id=nxb_nhanam.id,
            quantity=1,
            price=139000.0,
            book_title=books_data[2].title,
            book_cover=books_data[2].cover_image
        )
        db.add_all([item1_1, item1_2])

        # Đơn 2: Đang giao hàng
        order2 = models.Order(
            order_code="BH-260824-B994F1",
            buyer_id=buyer_vip.id,
            total_amount=96000.0,
            platform_fee_percent=5.0,
            platform_fee_amount=4800.0, # Sàn thu 4.8k
            seller_payout_amount=86400.0,
            shipping_name="Trần Minh Thư",
            shipping_phone="0934567890",
            shipping_address="128 Nguyễn Trãi, Quận 1, TP.HCM",
            shipping_carrier="Viettel Post",
            payment_method="VNPAY",
            status=models.OrderStatus.SHIPPING.value,
            tracking_step=3, # Đang giao
            created_at=datetime.datetime.utcnow() - datetime.timedelta(days=1)
        )
        db.add(order2)
        db.flush()

        item2_1 = models.OrderItem(
            order_id=order2.id,
            book_id=books_data[1].id, # Doraemon x2
            seller_id=nxb_kd.id,
            quantity=2,
            price=48000.0,
            book_title=books_data[1].title,
            book_cover=books_data[1].cover_image
        )
        db.add(item2_1)
        db.flush()

        # Khởi tạo danh sách thông báo mẫu cho NXB (Đơn hàng từ khách & Hệ thống)
        now_utc = datetime.datetime.utcnow()
        sample_notifs = [
            models.Notification(
                user_id=nxb_nhanam.id,
                title="Đơn hàng mới từ khách hàng",
                message=f"Bạn có đơn hàng mới #{order1.order_code} từ khách hàng Nguyễn Văn An (Tổng tiền: 214.000 đ). Vui lòng chuẩn bị đóng gói.",
                type=models.NotificationType.ORDER_CREATED.value,
                reference_id=order1.id,
                is_read=False,
                created_at=now_utc - datetime.timedelta(minutes=15)
            ),
            models.Notification(
                user_id=nxb_nhanam.id,
                title="Khách hàng đã nhận hàng thành công",
                message="Khách hàng Trần Minh Thư đã xác nhận nhận thành công đơn hàng #BH-260824-B994F1. Doanh thu 192.600 đ đã cộng vào số dư ví.",
                type=models.NotificationType.ORDER_DELIVERED.value,
                reference_id=order1.id,
                is_read=False,
                created_at=now_utc - datetime.timedelta(hours=2)
            ),
            models.Notification(
                user_id=nxb_nhanam.id,
                title="Cảnh báo tồn kho thấp",
                message="Cuốn sách 'Đứa Trẻ Cát' trong kho của bạn chỉ còn tồn kho 4 cuốn (ngưỡng an toàn: 5 cuốn). Hãy bổ sung thêm hàng.",
                type=models.NotificationType.LOW_STOCK_ALERT.value,
                reference_id=books_data[0].id if books_data else None,
                is_read=False,
                created_at=now_utc - datetime.timedelta(hours=5)
            ),
            models.Notification(
                user_id=nxb_nhanam.id,
                title="Đánh giá 5 sao từ khách hàng",
                message="Khách hàng Trần Minh Thư vừa đánh giá ⭐⭐⭐⭐⭐: 'Sách đóng gói cực kỳ cẩn thận, bìa cứng cáp và giao hàng siêu nhanh!'",
                type=models.NotificationType.ORDER_REVIEWED.value,
                reference_id=order1.id,
                is_read=True,
                created_at=now_utc - datetime.timedelta(hours=8)
            ),
            models.Notification(
                user_id=nxb_nhanam.id,
                title="Sách đã được phê duyệt",
                message=f"Cuốn sách '{books_data[0].title if books_data else 'Sách mới'}' của bạn đã được Admin duyệt và chính thức mở bán trên sàn!",
                type=models.NotificationType.BOOK_APPROVED.value,
                reference_id=books_data[0].id if books_data else None,
                is_read=True,
                created_at=now_utc - datetime.timedelta(days=1)
            ),
            models.Notification(
                user_id=nxb_nhanam.id,
                title="Thông báo từ Ban Quản Trị BookHub",
                message="BookHub triển khai chương trình 'Tháng Vàng Tri Ân Độc Giả' - Trợ giá 50% phí vận chuyển toàn quốc cho các gian hàng NXB chính hãng.",
                type=models.NotificationType.SYSTEM_ANNOUNCEMENT.value,
                reference_id=None,
                is_read=False,
                created_at=now_utc - datetime.timedelta(hours=12)
            ),
        ]
        db.add_all(sample_notifs)

        db.commit()
        added = sync_reference_catalog(db)
        db.commit()
        print("Đã khởi tạo xong dữ liệu mẫu thành công cho BookHub Platform!")
        if added:
            print(f"Đã bổ sung {added} sản phẩm tham chiếu vào catalog.")
    except Exception as e:
        db.rollback()
        print(f"Lỗi khi khởi tạo seed data: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
