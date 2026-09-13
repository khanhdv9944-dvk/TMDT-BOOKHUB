import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base, migrate_schema
from routes.auth_routes import router as auth_router
from routes.books_routes import router as books_router
from routes.orders_routes import router as orders_router
from routes.seller_routes import router as seller_router
from routes.admin_routes import router as admin_router
from routes.vip_routes import router as vip_router
from routes.notification_routes import router as notification_router
from routes.reviews_routes import router as reviews_router
from routes.returns_routes import buyer_router, seller_router as seller_return_router, admin_router as admin_return_router
from seed_data import seed_database

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

# Khởi tạo Database & Seed Data một lần duy nhất
_db_initialized = False

def initialize_database():
    global _db_initialized
    if _db_initialized:
        return
    try:
        Base.metadata.create_all(bind=engine)
        migrate_schema()
        seed_database()
        _db_initialized = True
    except Exception as e:
        print(f"Database initialization error: {e}")
        _db_initialized = True  # Đánh dấu đã try, tránh loop

# Khởi tạo DB ngay trên startup nếu không phải Vercel
if not os.getenv("VERCEL"):
    initialize_database()

app = FastAPI(
    title="BookHub - Sàn TMĐT Sách Đa Vai Trò",
    description="Nền tảng TMĐT Sách kết nối Độc giả, NXB/Tiệm sách và Chủ sàn với 3 nguồn doanh thu.",
    version="1.0.0"
)

# Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup event - khởi tạo DB một lần trên Vercel
@app.on_event("startup")
async def startup_event():
    if os.getenv("VERCEL"):
        initialize_database()

# Health check endpoint
@app.get("/health", include_in_schema=False)
async def health_check():
    return {"status": "ok", "environment": os.getenv("VERCEL", "local")}

# Đăng ký các Router API
app.include_router(auth_router)
app.include_router(books_router)
app.include_router(orders_router)
app.include_router(seller_router)
app.include_router(admin_router)
app.include_router(vip_router)
app.include_router(notification_router)
app.include_router(reviews_router)
app.include_router(buyer_router)
app.include_router(seller_return_router)
app.include_router(admin_return_router)

# Mount static assets explicitly so Vercel serves the same URLs as local FastAPI.
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/css", StaticFiles(directory=str(STATIC_DIR / "css")), name="css")
app.mount("/js", StaticFiles(directory=str(STATIC_DIR / "js")), name="js")

@app.get("/", include_in_schema=False)
def frontend_shell():
    return FileResponse(str(STATIC_DIR / "index.html"))

@app.get("/books/{book_id}", include_in_schema=False)
def book_detail_shell(book_id: int):
    return FileResponse(str(STATIC_DIR / "index.html"))

@app.get("/admin", include_in_schema=False)
@app.get("/admin/{admin_path:path}", include_in_schema=False)
def admin_shell(admin_path: str = ""):
    return FileResponse(str(STATIC_DIR / "index.html"))

@app.get("/terms", include_in_schema=False)
def terms_page():
    return frontend_shell()

@app.get("/privacy", include_in_schema=False)
def privacy_page():
    return frontend_shell()

@app.get("/{content_path:path}", include_in_schema=False)
def content_page_shell(content_path: str):
    allowed_paths = {
        "login", "register", "bookstores", "account", "account/addresses", "account/history", "account/orders",
        "support/terms", "support/privacy", "support/payment-security", "support/about", "support/returns",
        "support/warranty", "support/shipping", "support/wholesale", "support/faq", "support/contact",
    }
    if content_path in allowed_paths:
        return frontend_shell()
    raise HTTPException(status_code=404, detail="Không tìm thấy trang")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
