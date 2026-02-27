import os
from dotenv import load_dotenv
load_dotenv()  # Load .env before any other imports that read env vars

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from database import engine, Base
from routes.vendor import router as vendor_router
from routes.verification import router as verification_router
from routes.invoice import router as invoice_router
from routes.marketplace import router as marketplace_router
from routes.auth import router as auth_router
from routes.dashboard import router as dashboard_router
from routes.notifications import router as notifications_router
from routes.activity import router as activity_router
from routes.seed import router as seed_router
from routes.payment import router as payment_router
from routes.blockchain import router as blockchain_router
from routes.govt_api import router as govt_api_router
from routes.kyc import router as kyc_router
from routes.blockchain_registry import router as blockchain_registry_router
from routes.triple_verification import router as triple_verification_router
from routes.credit_scoring import router as credit_scoring_router
from routes.factoring import router as factoring_router
from routes.emandate import router as emandate_router
from routes.ai_negotiator import router as ai_negotiator_router
from routes.admin import router as admin_router

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="InvoX API",
    description="Embedded Invoice Financing Platform for MSMEs",
    version="3.0.0",
)

# CORS — allow localhost + all Vercel/Cloud Run preview/production URLs
_allowed_origins = [
    "http://localhost:3000",
    os.environ.get("FRONTEND_URL", ""),
]
# Also allow any *.vercel.app or *.run.app subdomain
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o for o in _allowed_origins if o],
    allow_origin_regex=r"https://.*\.(vercel\.app|run\.app)",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(vendor_router)
app.include_router(verification_router)
app.include_router(invoice_router)
app.include_router(marketplace_router)
app.include_router(dashboard_router)
app.include_router(notifications_router)
app.include_router(activity_router)
app.include_router(seed_router)
app.include_router(payment_router)
app.include_router(blockchain_router)
app.include_router(govt_api_router)
app.include_router(kyc_router)
app.include_router(blockchain_registry_router)
app.include_router(triple_verification_router)
app.include_router(credit_scoring_router)
app.include_router(factoring_router)
app.include_router(emandate_router)
app.include_router(ai_negotiator_router)
app.include_router(admin_router)

# Serve uploaded files (business photos, documents)
_upload_dir = "/tmp/uploads" if os.environ.get("VERCEL") else "uploads"
os.makedirs(_upload_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=_upload_dir), name="uploads")


@app.get("/")
def root():
    return {"message": "InvoX API is running", "version": "3.0.0"}


@app.get("/health")
def health():
    return {"status": "healthy"}
