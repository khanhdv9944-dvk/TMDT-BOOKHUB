import os
from fastapi import FastAPI
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
from seed_data import seed_database

# Khởi tạo Database & Seed Data
Base.metadata.create_all(bind=engine)
migrate_schema()
seed_database()

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

# Đăng ký các Router API
app.include_router(auth_router)
app.include_router(books_router)
app.include_router(orders_router)
app.include_router(seller_router)
app.include_router(admin_router)
app.include_router(vip_router)

# Mount thư mục Static phục vụ Giao diện Web
os.makedirs("static", exist_ok=True)
os.makedirs("static/css", exist_ok=True)
os.makedirs("static/js", exist_ok=True)

@app.get("/books/{book_id}", include_in_schema=False)
def book_detail_shell(book_id: int):
    return FileResponse("static/index.html")

@app.get("/admin", include_in_schema=False)
@app.get("/admin/{admin_path:path}", include_in_schema=False)
def admin_shell(admin_path: str = ""):
    return FileResponse("static/index.html")

app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
