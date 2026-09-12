from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

import models, auth
from database import get_db

router = APIRouter(prefix="/api", tags=["Reviews"])


def _serialize_review(db: Session, review: models.Review):
    buyer = review.user
    product = review.product
    images = [{
        "id": image.id,
        "image_url": image.image_url,
        "created_at": image.created_at,
    } for image in (review.images or [])]
    reply = None
    if review.seller_reply:
        reply = {
            "id": review.seller_reply.id,
            "seller_id": review.seller_reply.seller_id,
            "content": review.seller_reply.content,
            "created_at": review.seller_reply.created_at,
            "updated_at": review.seller_reply.updated_at,
        }
    return {
        "id": review.id,
        "user_id": review.user_id,
        "order_id": review.order_id,
        "order_item_id": review.order_item_id,
        "product_id": review.product_id,
        "seller_id": review.seller_id,
        "rating": review.rating,
        "content": review.content,
        "status": review.status,
        "created_at": review.created_at,
        "updated_at": review.updated_at,
        "buyer_name": buyer.full_name or buyer.username,
        "buyer_avatar": buyer.avatar,
        "product_name": product.title if product else None,
        "images": images,
        "reply": reply,
        "is_bought": True,
    }


def _refresh_product_rating(db: Session, product_id: int):
    book = db.query(models.Book).filter(models.Book.id == product_id).first()
    if not book:
        return
    aggregate = db.query(
        func.count(models.Review.id),
        func.avg(models.Review.rating),
    ).filter(
        models.Review.product_id == product_id,
        models.Review.status != models.ReviewStatus.HIDDEN.value,
    ).one()
    review_count, avg_rating = aggregate
    if review_count and avg_rating is not None:
        book.rating = round(float(avg_rating), 1)
    else:
        book.rating = 5.0
    db.commit()


@router.post("/reviews", response_model=dict)
def create_review(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    order_id = int(payload.get("order_id"))
    order_item_id = int(payload.get("order_item_id"))
    product_id = int(payload.get("product_id"))
    rating = int(payload.get("rating"))
    content = (payload.get("content") or "").strip()
    image_urls = payload.get("images") or []

    if rating < 1 or rating > 5:
        raise HTTPException(status_code=400, detail="Số sao phải nằm trong khoảng 1-5")
    if not content:
        raise HTTPException(status_code=400, detail="Nội dung đánh giá không được để trống")
    if len(image_urls) > 5:
        raise HTTPException(status_code=400, detail="Bạn chỉ được upload tối đa 5 ảnh")
    for image_url in image_urls:
        if isinstance(image_url, str) and len(image_url) > 1000:
            raise HTTPException(status_code=400, detail="URL ảnh quá dài")

    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng")
    if order.buyer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Bạn không có quyền đánh giá đơn hàng này")
    if order.status != models.OrderStatus.DELIVERED.value:
        raise HTTPException(status_code=400, detail="Chỉ có thể đánh giá sau khi đơn hàng đã giao thành công")

    order_item = db.query(models.OrderItem).filter(models.OrderItem.id == order_item_id, models.OrderItem.order_id == order_id).first()
    if not order_item:
        raise HTTPException(status_code=404, detail="Sản phẩm không thuộc đơn hàng này")
    if order_item.book_id != product_id:
        raise HTTPException(status_code=400, detail="Sản phẩm không khớp với mục trong đơn hàng")

    existing = db.query(models.Review).filter(
        models.Review.order_item_id == order_item_id,
        models.Review.user_id == current_user.id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Bạn đã đánh giá sản phẩm này rồi. Vui lòng chỉnh sửa đánh giá hiện có.")

    product = db.query(models.Book).filter(models.Book.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm")
    if product.seller_id != order_item.seller_id:
        raise HTTPException(status_code=400, detail="Sản phẩm không hợp lệ cho đánh giá")

    review = models.Review(
        user_id=current_user.id,
        order_id=order.id,
        order_item_id=order_item.id,
        product_id=product.id,
        seller_id=product.seller_id,
        rating=rating,
        content=content,
        status=models.ReviewStatus.REVIEWED.value,
    )
    db.add(review)
    db.flush()

    for image_url in image_urls:
        if not image_url:
            continue
        db.add(models.ReviewImage(review_id=review.id, image_url=image_url))

    db.commit()
    db.refresh(review)
    _refresh_product_rating(db, product.id)
    return _serialize_review(db, review)


@router.patch("/reviews/{review_id}", response_model=dict)
def update_review(
    review_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    review = db.query(models.Review).filter(models.Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Không tìm thấy đánh giá")
    if review.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Bạn không có quyền chỉnh sửa đánh giá này")

    rating = payload.get("rating")
    content = payload.get("content")
    image_urls = payload.get("images")

    if rating is not None:
        rating = int(rating)
        if rating < 1 or rating > 5:
            raise HTTPException(status_code=400, detail="Số sao phải nằm trong khoảng 1-5")
        review.rating = rating
    if content is not None:
        content = str(content).strip()
        if not content:
            raise HTTPException(status_code=400, detail="Nội dung đánh giá không được để trống")
        review.content = content
    if image_urls is not None:
        if len(image_urls) > 5:
            raise HTTPException(status_code=400, detail="Bạn chỉ được upload tối đa 5 ảnh")
        existing_images = db.query(models.ReviewImage).filter(models.ReviewImage.review_id == review.id).all()
        for image in existing_images:
            db.delete(image)
        for image_url in image_urls:
            if image_url:
                db.add(models.ReviewImage(review_id=review.id, image_url=image_url))

    review.status = models.ReviewStatus.EDITED.value
    review.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(review)
    _refresh_product_rating(db, review.product_id)
    return _serialize_review(db, review)


@router.get("/reviews/product/{product_id}", response_model=dict)
def get_product_reviews(
    product_id: int,
    db: Session = Depends(get_db),
):
    reviews_query = db.query(models.Review).filter(
        models.Review.product_id == product_id,
        models.Review.status != models.ReviewStatus.HIDDEN.value,
    ).order_by(models.Review.created_at.desc())
    reviews = reviews_query.all()
    total = len(reviews)
    distribution = {str(star): 0 for star in [5, 4, 3, 2, 1]}
    for review in reviews:
        distribution[str(review.rating)] = distribution.get(str(review.rating), 0) + 1
    avg_value = round(sum(review.rating for review in reviews) / total, 1) if total else 0.0
    return {
        "product_id": product_id,
        "total_reviews": total,
        "average_rating": avg_value,
        "rating_distribution": distribution,
        "reviews": [_serialize_review(db, review) for review in reviews],
    }


@router.get("/reviews/my", response_model=List[dict])
def get_my_reviews(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    reviews = db.query(models.Review).filter(models.Review.user_id == current_user.id).order_by(models.Review.created_at.desc()).all()
    return [_serialize_review(db, review) for review in reviews]


@router.get("/reviews/{review_id}", response_model=dict)
def get_review_detail(
    review_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    review = db.query(models.Review).filter(models.Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Không tìm thấy đánh giá")
    if current_user.role not in [models.UserRole.ADMIN.value, models.UserRole.SELLER.value] and review.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền xem đánh giá này")
    return _serialize_review(db, review)


@router.post("/reviews/{review_id}/seller-reply", response_model=dict)
def create_seller_reply(
    review_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    review = db.query(models.Review).filter(models.Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Không tìm thấy đánh giá")
    if current_user.role != models.UserRole.SELLER.value or review.seller_id != current_user.id:
        raise HTTPException(status_code=403, detail="Bạn không có quyền phản hồi đánh giá này")

    content = (payload.get("content") or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="Nội dung phản hồi không được để trống")

    existing = review.seller_reply
    if existing:
        existing.content = content
        existing.updated_at = datetime.utcnow()
        db.commit(); db.refresh(existing)
        return {
            "id": existing.id,
            "reply": {
                "id": existing.id,
                "seller_id": existing.seller_id,
                "content": existing.content,
                "created_at": existing.created_at,
                "updated_at": existing.updated_at,
            }
        }

    reply = models.SellerReply(review_id=review.id, seller_id=current_user.id, content=content)
    db.add(reply)
    db.commit(); db.refresh(reply)
    return {
        "id": reply.id,
        "reply": {
            "id": reply.id,
            "seller_id": reply.seller_id,
            "content": reply.content,
            "created_at": reply.created_at,
            "updated_at": reply.updated_at,
        }
    }


@router.get("/seller/reviews", response_model=List[dict])
def get_seller_reviews(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.UserRole.SELLER.value, models.UserRole.ADMIN.value])),
):
    if current_user.role == models.UserRole.ADMIN.value:
        reviews = db.query(models.Review).order_by(models.Review.created_at.desc()).all()
    else:
        reviews = db.query(models.Review).filter(models.Review.seller_id == current_user.id).order_by(models.Review.created_at.desc()).all()
    return [_serialize_review(db, review) for review in reviews]


@router.get("/admin/reviews", response_model=List[dict])
def list_admin_reviews(
    product_id: Optional[int] = Query(None),
    seller_id: Optional[int] = Query(None),
    rating: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.UserRole.ADMIN.value])),
):
    query = db.query(models.Review)
    if product_id:
        query = query.filter(models.Review.product_id == product_id)
    if seller_id:
        query = query.filter(models.Review.seller_id == seller_id)
    if rating:
        query = query.filter(models.Review.rating == rating)
    if status:
        query = query.filter(models.Review.status == status)
    if q:
        query = query.filter(models.Review.content.ilike(f"%{q}%"))
    query = query.order_by(models.Review.created_at.desc())
    return [_serialize_review(db, review) for review in query.all()]


@router.patch("/admin/reviews/{review_id}/hide", response_model=dict)
def hide_review(
    review_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.UserRole.ADMIN.value])),
):
    review = db.query(models.Review).filter(models.Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Không tìm thấy đánh giá")
    review.status = models.ReviewStatus.HIDDEN.value
    review.updated_at = datetime.utcnow()
    db.commit(); db.refresh(review)
    _refresh_product_rating(db, review.product_id)
    return _serialize_review(db, review)


@router.patch("/admin/reviews/{review_id}/show", response_model=dict)
def show_review(
    review_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role([models.UserRole.ADMIN.value])),
):
    review = db.query(models.Review).filter(models.Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Không tìm thấy đánh giá")
    review.status = models.ReviewStatus.REVIEWED.value if review.status == models.ReviewStatus.HIDDEN.value else review.status
    review.updated_at = datetime.utcnow()
    db.commit(); db.refresh(review)
    _refresh_product_rating(db, review.product_id)
    return _serialize_review(db, review)
