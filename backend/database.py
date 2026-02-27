from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Use /tmp on Vercel serverless (read-only filesystem except /tmp)
if os.environ.get("VERCEL"):
    DATABASE_URL = "sqlite:////tmp/invox.db"
else:
    DATABASE_URL = "sqlite:///./invox.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
