"""
Migration script to add Telegram and OCR fields to the existing database.
Run this once after updating models.py.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "invox.db")


def migrate():
    if not os.path.exists(DB_PATH):
        print("No database found. Tables will be created on server start.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # ── Add telegram columns to users table ──
    user_columns = {
        "telegram_chat_id": "VARCHAR(50) UNIQUE",
        "telegram_username": "VARCHAR(100)",
        "telegram_link_code": "VARCHAR(10) UNIQUE",
        "telegram_link_code_expires": "DATETIME",
    }

    for col_name, col_type in user_columns.items():
        try:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
            print(f"  ✅ Added users.{col_name}")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print(f"  ⏭️  users.{col_name} already exists")
            else:
                print(f"  ❌ Error adding users.{col_name}: {e}")

    # ── Add OCR / telegram columns to invoices table ──
    invoice_columns = {
        "file_path": "VARCHAR(500)",
        "ocr_status": "VARCHAR(20)",
        "ocr_confidence": "FLOAT",
        "ocr_raw_text": "TEXT",
        "ocr_warnings": "TEXT",
        "source": "VARCHAR(20)",
    }

    for col_name, col_type in invoice_columns.items():
        try:
            cursor.execute(f"ALTER TABLE invoices ADD COLUMN {col_name} {col_type}")
            print(f"  ✅ Added invoices.{col_name}")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print(f"  ⏭️  invoices.{col_name} already exists")
            else:
                print(f"  ❌ Error adding invoices.{col_name}: {e}")

    conn.commit()
    conn.close()
    print("\n✅ Migration complete!")


if __name__ == "__main__":
    migrate()
