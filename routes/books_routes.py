from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc
from database import get_db
import models, schemas, auth

router = APIRouter(prefix="/api/books", tags=["Books"])

@router.get("/categories", response_model=List[schemas.CategoryOut])
def get_categories(db: Session = Depends(get_db)):
    return db.query(models.Category).all()

@router.get("/sellers")
def list_public_sellers(db: Session = Depends(get_db)):
    sellers = db.query(models.User).filter(
        models.User.role == models.UserRole.SELLER.value,
        models.User.status.in_([models.UserStatus.ACTIVE.value, models.UserStatus.APPROVED.value]),
    ).order_by(models.User.shop_name, models.User.full_name).all()
    return [{
        "id": seller.id,
        "shop_name": seller.shop_name or seller.full_name or seller.username,
        "description": seller.shop_description,
        "logo": seller.shop_logo or seller.avatar,
        "book_count": sum(1 for book in seller.books if book.status == models.BookStatus.APPROVED.value and getattr(book, 'is_visible', True) and not getattr(book, 'is_out_of_stock', False)),
    } for seller in sellers]

@router.get("", response_model=List[schemas.BookOut])
def list_books(
    q: Optional[str] = Query(None, description="Tìm theo tên sách hoặc tác giả"),
    category_id: Optional[int] = Query(None, description="Lọc theo mã thể loại"),
    seller_id: Optional[int] = Query(None, description="Lọc theo nhà bán hàng / NXB"),
    is_featured: Optional[bool] = Query(None, description="Lọc sách có quảng cáo"),
    limit: int = 50,
    db: Session = Depends(get_db)
):
    query = db.query(models.Book).filter(
        models.Book.status == models.BookStatus.APPROVED.value,
        models.Book.is_visible.is_(True),
        models.Book.is_out_of_stock.is_(False)
    )
    
    if q:
        search_pattern = f"%{q}%"
        query = query.filter(
            or_(
                models.Book.title.ilike(search_pattern),
                models.Book.author.ilike(search_pattern),
                models.Book.publisher.ilike(search_pattern)
            )
        )
    
    if category_id:
        query = query.filter(models.Book.category_id == category_id)

    if seller_id:
        query = query.filter(models.Book.seller_id == seller_id)
        
    if is_featured is not None:
        query = query.filter(models.Book.is_featured_ad == is_featured)

    # Ưu tiên sách có Quảng cáo tài trợ lên đầu (Featured Ad Top), sau đó đến bán chạy / mới nhất
    books = query.order_by(
        desc(models.Book.is_featured_ad),
        desc(models.Book.sold_count),
        desc(models.Book.created_at)
    ).limit(limit).all()

    # Thêm thông tin liên quan
    results = []
    for b in books:
        book_dict = {
            "id": b.id,
            "seller_id": b.seller_id,
            "category_id": b.category_id,
            "title": b.title,
            "author": b.author,
            "publisher": b.publisher,
            "price": b.price,
            "discount_price": b.discount_price,
            "stock": b.stock,
            "cover_image": b.cover_image,
            "description": b.description,
            "book_format": b.book_format or ("EBOOK" if b.full_ebook_content else "PAPER"),
            "cover_type": b.cover_type or "SOFT",
            "vip_eligible": bool(b.vip_eligible or b.full_ebook_content),
            "sample_content": b.sample_content,
            "full_ebook_content": None, # Không trả về full text trong danh sách
            "status": b.status,
            "is_featured_ad": b.is_featured_ad,
            "sold_count": b.sold_count,
            "rating": b.rating,
            "created_at": b.created_at,
            "seller_shop_name": b.seller.shop_name if b.seller else "NXB Chính hãng",
            "category_name": b.category.name if b.category else "Tổng hợp",
            "is_visible": getattr(b, 'is_visible', True),
            "is_out_of_stock": getattr(b, 'is_out_of_stock', False),
            "rejection_reason": getattr(b, 'rejection_reason', None)
        }
        results.append(book_dict)
    return results

@router.get("/recommendations", response_model=List[schemas.BookOut])
def get_recommendations(db: Session = Depends(get_db)):
    """Gợi ý sách hợp gu độc giả: kết hợp sách đánh giá cao, bán chạy và tuyển chọn"""
    books = db.query(models.Book).filter(
        models.Book.status == models.BookStatus.APPROVED.value,
        models.Book.is_visible.is_(True),
        models.Book.is_out_of_stock.is_(False)
    ).order_by(desc(models.Book.rating), desc(models.Book.sold_count)).limit(6).all()

    results = []
    for b in books:
        results.append({
            "id": b.id,
            "seller_id": b.seller_id,
            "category_id": b.category_id,
            "title": b.title,
            "author": b.author,
            "publisher": b.publisher,
            "price": b.price,
            "discount_price": b.discount_price,
            "stock": b.stock,
            "cover_image": b.cover_image,
            "description": b.description,
            "book_format": b.book_format or ("EBOOK" if b.full_ebook_content else "PAPER"),
            "cover_type": b.cover_type or "SOFT",
            "vip_eligible": bool(b.vip_eligible or b.full_ebook_content),
            "sample_content": b.sample_content,
            "full_ebook_content": None,
            "status": b.status,
            "is_featured_ad": b.is_featured_ad,
            "sold_count": b.sold_count,
            "rating": b.rating,
            "created_at": b.created_at,
            "seller_shop_name": b.seller.shop_name if b.seller else "NXB Chính hãng",
            "category_name": b.category.name if b.category else "Tổng hợp",
            "is_visible": getattr(b, 'is_visible', True),
            "is_out_of_stock": getattr(b, 'is_out_of_stock', False),
            "rejection_reason": getattr(b, 'rejection_reason', None)
        })
    return results

@router.get("/{book_id}")
def get_book_detail(
    book_id: int, 
    db: Session = Depends(get_db), 
    current_user: Optional[models.User] = Depends(auth.get_current_user_optional)
):
    book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Không tìm thấy sách")
    
    can_read_full = False
    if current_user:
        if current_user.is_vip or current_user.role == models.UserRole.ADMIN.value or current_user.id == book.seller_id:
            can_read_full = True

    return {
        "id": book.id,
        "seller_id": book.seller_id,
        "category_id": book.category_id,
        "title": book.title,
        "author": book.author,
        "publisher": book.publisher,
        "price": book.price,
        "discount_price": book.discount_price,
        "stock": book.stock,
        "cover_image": book.cover_image,
        "description": book.description,
        "book_format": book.book_format or ("EBOOK" if book.full_ebook_content else "PAPER"),
        "cover_type": book.cover_type or "SOFT",
        "vip_eligible": bool(book.vip_eligible or book.full_ebook_content),
        "sample_content": book.sample_content,
        "full_ebook_content": book.full_ebook_content if can_read_full else None,
        "can_read_full": can_read_full,
        "status": book.status,
        "is_featured_ad": book.is_featured_ad,
        "sold_count": book.sold_count,
        "rating": book.rating,
        "created_at": book.created_at,
        "is_visible": getattr(book, 'is_visible', True),
        "is_out_of_stock": getattr(book, 'is_out_of_stock', False),
        "seller": {
            "id": book.seller.id,
            "shop_name": book.seller.shop_name or book.seller.full_name,
            "status": book.seller.status,
            "avatar": book.seller.avatar
        } if book.seller else None,
        "category": {
            "id": book.category.id,
            "name": book.category.name,
            "slug": book.category.slug
        } if book.category else None
    }
