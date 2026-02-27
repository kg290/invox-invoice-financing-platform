"""Add verification columns to lenders table."""
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE lenders ADD COLUMN pan_number VARCHAR(10)"))
        print("Added pan_number")
    except Exception as e:
        print(f"pan_number: {e}")
    try:
        conn.execute(text("ALTER TABLE lenders ADD COLUMN aadhaar_number VARCHAR(12)"))
        print("Added aadhaar_number")
    except Exception as e:
        print(f"aadhaar_number: {e}")
    try:
        conn.execute(text("ALTER TABLE lenders ADD COLUMN verification_status VARCHAR(20) NOT NULL DEFAULT 'unverified'"))
        print("Added verification_status")
    except Exception as e:
        print(f"verification_status: {e}")
    conn.commit()
    print("Done!")
