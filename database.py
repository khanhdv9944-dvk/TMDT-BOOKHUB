import os
import shutil
from pathlib import Path
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

BASE_DIR = Path(__file__).resolve().parent
SOURCE_DB_PATH = BASE_DIR / "bookhub.db"
if os.getenv("VERCEL"):
    DB_PATH = Path("/tmp/bookhub.db")
    if not DB_PATH.exists() and SOURCE_DB_PATH.exists():
        shutil.copy2(SOURCE_DB_PATH, DB_PATH)
else:
    DB_PATH = SOURCE_DB_PATH
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def migrate_schema():
    """Apply the small additive migration needed by the existing SQLite database."""
    inspector = inspect(engine)
    if "orders" in inspector.get_table_names():
        order_columns = {column["name"] for column in inspector.get_columns("orders")}
        additions = {
            "shipping_province": "VARCHAR(100)",
            "shipping_province_code": "VARCHAR(20)",
            "shipping_district": "VARCHAR(100)",
            "shipping_district_code": "VARCHAR(20)",
            "shipping_ward": "VARCHAR(100)",
            "shipping_ward_code": "VARCHAR(20)",
            "shipping_street": "VARCHAR(255)",
            "shipping_method": "VARCHAR(30) DEFAULT 'STANDARD'",
            "shipping_fee": "FLOAT DEFAULT 30000",
            "subtotal_amount": "FLOAT DEFAULT 0",
            "discount_amount": "FLOAT DEFAULT 0",
            "voucher_code": "VARCHAR(50)",
            "terms_accepted": "BOOLEAN DEFAULT 0 NOT NULL",
            "tracking_number": "VARCHAR(50)",
            "return_status": "VARCHAR(30) DEFAULT 'NONE'",
            "return_reason": "TEXT",
        }
        with engine.begin() as connection:
            for name, definition in additions.items():
                if name not in order_columns:
                    connection.execute(text(f"ALTER TABLE orders ADD COLUMN {name} {definition}"))

    if "books" in inspector.get_table_names():
        book_columns = {column["name"] for column in inspector.get_columns("books")}
        book_additions = {
            "book_format": "VARCHAR(20) DEFAULT 'PAPER' NOT NULL",
            "cover_type": "VARCHAR(20) DEFAULT 'SOFT' NOT NULL",
            "vip_eligible": "BOOLEAN DEFAULT 0 NOT NULL",
            "isbn": "VARCHAR(50)",
            "translator": "VARCHAR(150)",
            "page_count": "INTEGER",
            "publication_year": "INTEGER",
            "language": "VARCHAR(50) DEFAULT 'Tiếng Việt'",
            "preview_file_url": "VARCHAR(500)",
        }
        with engine.begin() as connection:
            for name, definition in book_additions.items():
                if name not in book_columns:
                    connection.execute(text(f"ALTER TABLE books ADD COLUMN {name} {definition}"))

    if "users" in inspector.get_table_names():
        user_columns = {column["name"] for column in inspector.get_columns("users")}
        user_additions = {
            "business_type": "VARCHAR(50)",
            "company_name": "VARCHAR(150)",
            "company_email": "VARCHAR(100)",
            "company_phone": "VARCHAR(20)",
            "legal_representative_name": "VARCHAR(100)",
            "legal_representative_position": "VARCHAR(100)",
            "legal_representative_id_number": "VARCHAR(30)",
            "office_province": "VARCHAR(100)",
            "office_district": "VARCHAR(100)",
            "office_ward": "VARCHAR(100)",
            "office_street": "VARCHAR(255)",
            "shipping_same_as_office": "BOOLEAN DEFAULT 1 NOT NULL",
            "shipping_province": "VARCHAR(100)",
            "shipping_district": "VARCHAR(100)",
            "shipping_ward": "VARCHAR(100)",
            "shipping_street": "VARCHAR(255)",
            "tax_code": "VARCHAR(50)",
            "bank_name": "VARCHAR(100)",
            "bank_account_number": "VARCHAR(50)",
            "bank_account_holder": "VARCHAR(100)",
            "warehouse_address": "VARCHAR(255)",
            "shop_logo": "VARCHAR(500)",
            "shop_banner": "VARCHAR(500)",
            "rejection_reason": "TEXT",
            "rejected_at": "DATETIME",
            "rejected_by": "INTEGER",
        }
        with engine.begin() as connection:
            for name, definition in user_additions.items():
                if name not in user_columns:
                    connection.execute(text(f"ALTER TABLE users ADD COLUMN {name} {definition}"))

    if "users" in inspector.get_table_names():
        user_columns = {column["name"] for column in inspector.get_columns("users")}
        seller_review_columns = {
            "approved_at": "DATETIME",
            "approved_by": "INTEGER",
        }
        with engine.begin() as connection:
            for name, definition in seller_review_columns.items():
                if name not in user_columns:
                    connection.execute(text(f"ALTER TABLE users ADD COLUMN {name} {definition}"))

    if "vouchers" in inspector.get_table_names():
        voucher_columns = {column["name"] for column in inspector.get_columns("vouchers")}
        voucher_additions = {
            "seller_id": "INTEGER",
        }
        with engine.begin() as connection:
            for name, definition in voucher_additions.items():
                if name not in voucher_columns:
                    connection.execute(text(f"ALTER TABLE vouchers ADD COLUMN {name} {definition}"))

    if "books" in inspector.get_table_names():
        book_columns = {column["name"] for column in inspect(engine).get_columns("books")}
        book_additions = {
            "is_visible": "BOOLEAN DEFAULT 1 NOT NULL",
            "is_out_of_stock": "BOOLEAN DEFAULT 0 NOT NULL",
            "rejection_reason": "TEXT",
            "rejected_at": "DATETIME",
            "rejected_by": "INTEGER",
        }
        with engine.begin() as connection:
            for name, definition in book_additions.items():
                if name not in book_columns:
                    connection.execute(text(f"ALTER TABLE books ADD COLUMN {name} {definition}"))

    if "withdrawal_requests" in inspector.get_table_names():
        payout_columns = {column["name"] for column in inspect(engine).get_columns("withdrawal_requests")}
        payout_additions = {
            "rejection_reason": "TEXT",
            "processed_at": "DATETIME",
            "transaction_id": "VARCHAR(50)",
        }
        with engine.begin() as connection:
            for name, definition in payout_additions.items():
                if name not in payout_columns:
                    connection.execute(text(f"ALTER TABLE withdrawal_requests ADD COLUMN {name} {definition}"))

    if "addresses" in inspector.get_table_names():
        address_columns = {column["name"] for column in inspector.get_columns("addresses")}
        address_additions = {
            "province_code": "VARCHAR(20)",
            "district_code": "VARCHAR(20)",
            "ward_code": "VARCHAR(20)",
        }
        with engine.begin() as connection:
            for name, definition in address_additions.items():
                if name not in address_columns:
                    connection.execute(text(f"ALTER TABLE addresses ADD COLUMN {name} {definition}"))

    if "return_requests" in inspector.get_table_names():
        return_request_columns = {column["name"] for column in inspector.get_columns("return_requests")}
        return_request_additions = {
            "refund_method": "VARCHAR(50)",
            "admin_note": "TEXT",
            "shipped_at": "DATETIME",
            "received_at": "DATETIME",
            "cancelled_at": "DATETIME",
        }
        with engine.begin() as connection:
            for name, definition in return_request_additions.items():
                if name not in return_request_columns:
                    connection.execute(text(f"ALTER TABLE return_requests ADD COLUMN {name} {definition}"))

    additive_tables = {
        "transactions": "CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY, transaction_code VARCHAR(50) UNIQUE NOT NULL, seller_id INTEGER, order_id INTEGER, payout_id INTEGER, transaction_type VARCHAR(30) NOT NULL, gross_amount FLOAT NOT NULL DEFAULT 0, fee_amount FLOAT NOT NULL DEFAULT 0, net_amount FLOAT NOT NULL DEFAULT 0, status VARCHAR(30) NOT NULL DEFAULT 'PENDING', note TEXT, created_at DATETIME)",
        "disputes": "CREATE TABLE IF NOT EXISTS disputes (id INTEGER PRIMARY KEY, dispute_code VARCHAR(50) UNIQUE NOT NULL, order_id INTEGER NOT NULL, buyer_id INTEGER NOT NULL, seller_id INTEGER NOT NULL, reason VARCHAR(255) NOT NULL, description TEXT NOT NULL, amount FLOAT NOT NULL DEFAULT 0, status VARCHAR(30) NOT NULL DEFAULT 'OPEN', buyer_response TEXT, seller_response TEXT, admin_decision VARCHAR(40), resolution_note TEXT, created_at DATETIME, updated_at DATETIME, resolved_at DATETIME, resolved_by INTEGER)",
        "documents": "CREATE TABLE IF NOT EXISTS documents (id INTEGER PRIMARY KEY, owner_id INTEGER NOT NULL, entity_type VARCHAR(30) NOT NULL, entity_id INTEGER NOT NULL, document_type VARCHAR(40) NOT NULL, file_name VARCHAR(255) NOT NULL, mime_type VARCHAR(100) NOT NULL, storage_path VARCHAR(500) NOT NULL, uploaded_at DATETIME, status VARCHAR(30) NOT NULL DEFAULT 'UPLOADED')",
        "notifications": "CREATE TABLE IF NOT EXISTS notifications (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, title VARCHAR(255) NOT NULL, message TEXT NOT NULL, type VARCHAR(50) NOT NULL, reference_id INTEGER, is_read BOOLEAN DEFAULT 0 NOT NULL, created_at DATETIME, FOREIGN KEY(user_id) REFERENCES users(id))",
        "seller_review_audit": "CREATE TABLE IF NOT EXISTS seller_review_audit (id INTEGER PRIMARY KEY, seller_id INTEGER NOT NULL, admin_id INTEGER, action VARCHAR(40) NOT NULL, previous_status VARCHAR(30), new_status VARCHAR(30), reason TEXT, created_at DATETIME)",
        "return_requests": "CREATE TABLE IF NOT EXISTS return_requests (id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL, user_id INTEGER NOT NULL, status VARCHAR(30) NOT NULL DEFAULT 'PENDING', reason VARCHAR(50) NOT NULL, description TEXT, refund_method VARCHAR(50), refund_amount FLOAT NOT NULL DEFAULT 0, rejection_reason TEXT, admin_note TEXT, created_at DATETIME, updated_at DATETIME, approved_at DATETIME, shipped_at DATETIME, received_at DATETIME, refunded_at DATETIME, cancelled_at DATETIME)",
        "return_request_items": "CREATE TABLE IF NOT EXISTS return_request_items (id INTEGER PRIMARY KEY, return_request_id INTEGER NOT NULL, order_item_id INTEGER NOT NULL, product_id INTEGER NOT NULL, quantity INTEGER NOT NULL, unit_price FLOAT NOT NULL, product_name VARCHAR(255))",
        "reviews": "CREATE TABLE IF NOT EXISTS reviews (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, order_id INTEGER NOT NULL, order_item_id INTEGER NOT NULL, product_id INTEGER NOT NULL, seller_id INTEGER NOT NULL, rating INTEGER NOT NULL, content TEXT NOT NULL, status VARCHAR(30) NOT NULL DEFAULT 'REVIEWED', created_at DATETIME, updated_at DATETIME)",
        "review_images": "CREATE TABLE IF NOT EXISTS review_images (id INTEGER PRIMARY KEY, review_id INTEGER NOT NULL, image_url VARCHAR(1000) NOT NULL, created_at DATETIME)",
        "seller_replies": "CREATE TABLE IF NOT EXISTS seller_replies (id INTEGER PRIMARY KEY, review_id INTEGER NOT NULL UNIQUE, seller_id INTEGER NOT NULL, content TEXT NOT NULL, created_at DATETIME, updated_at DATETIME)",
    }
    with engine.begin() as connection:
        existing = set(inspect(engine).get_table_names())
        for table_name, statement in additive_tables.items():
            if table_name not in existing:
                connection.execute(text(statement))
