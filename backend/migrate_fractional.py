"""Migration script: Add Community Pot / Fractional Funding columns."""
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    # Add new columns to marketplace_listings
    cols_to_add = [
        ("total_funded_amount", "FLOAT NOT NULL DEFAULT 0"),
        ("total_investors", "INTEGER NOT NULL DEFAULT 0"),
        ("min_investment", "FLOAT NOT NULL DEFAULT 500"),
        ("funding_mode", "VARCHAR(20) NOT NULL DEFAULT 'fractional'"),
    ]
    for col_name, col_def in cols_to_add:
        try:
            conn.execute(text(f"ALTER TABLE marketplace_listings ADD COLUMN {col_name} {col_def}"))
            print(f"  Added {col_name}")
        except Exception as e:
            if "duplicate column" in str(e).lower():
                print(f"  {col_name} already exists")
            else:
                print(f"  {col_name}: {e}")

    conn.commit()

    # Sync existing funded listings so data is consistent
    conn.execute(text(
        "UPDATE marketplace_listings SET total_funded_amount = COALESCE(funded_amount, 0) "
        "WHERE funded_amount IS NOT NULL AND total_funded_amount = 0"
    ))
    conn.execute(text(
        "UPDATE marketplace_listings SET total_investors = 1 "
        "WHERE lender_id IS NOT NULL AND total_investors = 0"
    ))
    conn.commit()
    print("  Synced existing funded listings")

print("Migration complete!")
