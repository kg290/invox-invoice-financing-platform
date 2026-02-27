"""
main.py — FastAPI app for the InvoX OCR Service.

Endpoints:
  POST /ocr/extract          — Upload an invoice (PDF/image) and get extracted fields
  POST /ocr/extract/{id}     — Same, but also patches the invoice via callback
  GET  /health               — Health check
  GET  /                     — Service info

On startup, attempts to connect to Redis and start the subscriber thread.
If Redis is unavailable, the HTTP upload endpoint still works standalone.
"""

import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.preprocessor import preprocess
from app.extractor import ocr_images, extract_invoice_data
from app.invoice_client import patch_invoice_ocr
from app.events import publish, OCR_COMPLETED, VERIFY_REQUESTED


# ── Lifespan: start Redis subscriber on boot ──
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("\n" + "=" * 50)
    print("  🚀 InvoX OCR Service starting...")
    print("=" * 50)

    # Try to start Redis subscriber (non-blocking)
    try:
        from app.subscriber import start_subscriber
        start_subscriber()
    except Exception as exc:
        print(f"  ⚠️  Redis subscriber not started: {exc}")
        print(f"  ℹ️  Direct HTTP upload is still available.")

    yield

    print("  🛑 InvoX OCR Service shutting down.")


app = FastAPI(
    title="InvoX OCR Service",
    description="AI-powered invoice text extraction using Tesseract OCR",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow the main backend and frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8000",
        os.environ.get("FRONTEND_URL", ""),
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Allowed file types ──
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/tiff",
    "image/bmp",
}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


@app.get("/")
def root():
    return {
        "service": "InvoX OCR Service",
        "version": "1.0.0",
        "endpoints": {
            "POST /ocr/extract": "Upload an invoice file for OCR extraction",
            "POST /ocr/extract/{invoice_id}": "Extract and patch invoice record",
            "GET /health": "Health check",
        },
    }


@app.get("/health")
def health():
    return {"status": "healthy", "service": "ocr-service"}


@app.post("/ocr/extract")
async def extract_invoice(
    file: UploadFile = File(..., description="Invoice file (PDF, JPG, PNG)"),
):
    """
    Upload an invoice file and extract structured fields via OCR.
    Returns extracted data without patching any external service.
    """
    return await _run_ocr_pipeline(file, invoice_id=None)


@app.post("/ocr/extract/{invoice_id}")
async def extract_and_patch(
    invoice_id: int,
    file: UploadFile = File(..., description="Invoice file (PDF, JPG, PNG)"),
    auth_token: str = Query(default=None, description="JWT token for invoice-service callback"),
):
    """
    Upload an invoice file, extract fields via OCR, and PATCH the invoice
    record on the main InvoX backend with the extracted data.
    Also publishes VERIFY_REQUESTED to Redis.
    """
    return await _run_ocr_pipeline(file, invoice_id=invoice_id, auth_token=auth_token)


async def _run_ocr_pipeline(
    file: UploadFile,
    invoice_id: int | None = None,
    auth_token: str | None = None,
) -> dict:
    """Core OCR pipeline handler."""
    start = time.time()

    # ── Validate file ──
    content_type = file.content_type or ""
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {content_type}. "
                   f"Accepted: PDF, JPG, PNG, TIFF, BMP."
        )

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Maximum 20 MB.")
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty file uploaded.")

    filename = file.filename or "unknown"
    is_pdf = content_type == "application/pdf" or filename.lower().endswith(".pdf")

    print(f"\n{'='*50}")
    print(f"  📄 OCR Request: {filename} ({len(file_bytes)} bytes)")
    if invoice_id:
        print(f"  🔗 Invoice ID: {invoice_id}")
    print(f"{'='*50}")

    # ── Step 1: Preprocess ──
    try:
        print("  🖼️  Step 1: Preprocessing...")
        images = preprocess(file_bytes, is_pdf=is_pdf)
        print(f"     → {len(images)} page(s) processed")
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Image preprocessing failed: {exc}")

    # ── Step 2: OCR ──
    try:
        print("  🔍 Step 2: Running Tesseract OCR...")
        raw_text = ocr_images(images)
        print(f"     → {len(raw_text)} characters extracted")
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"OCR extraction failed: {exc}")

    if not raw_text.strip():
        # Empty OCR — return mock/warning data instead of crashing
        elapsed = round(time.time() - start, 2)
        return {
            "success": False,
            "message": "OCR produced no text. The image may be blank, too blurry, or not a valid invoice.",
            "invoice_id": invoice_id,
            "data": {
                "invoice_number": None,
                "seller_gstin": None,
                "buyer_gstin": None,
                "seller_name": None,
                "buyer_name": None,
                "invoice_date": None,
                "due_date": None,
                "total_amount": 0.0,
                "line_items": [],
                "confidence_score": 0.0,
                "warnings": ["OCR produced empty text"],
            },
            "processing_time_seconds": elapsed,
        }

    # ── Step 3: Extract fields ──
    print("  📊 Step 3: Extracting structured fields...")
    extracted = extract_invoice_data(raw_text)
    extracted["raw_text_preview"] = raw_text[:1000]

    elapsed = round(time.time() - start, 2)
    print(f"  ✅ Done in {elapsed}s — confidence: {extracted['confidence_score']}")

    # ── Step 4 (optional): Patch invoice + publish events ──
    patch_result = None
    if invoice_id:
        print(f"  📡 Step 4: Patching invoice #{invoice_id}...")
        patch_result = await patch_invoice_ocr(invoice_id, extracted, auth_token)

        # Publish Redis events
        event_payload = {
            "invoice_id": invoice_id,
            "confidence_score": extracted["confidence_score"],
            "status": "ocr_done",
        }
        publish(OCR_COMPLETED, event_payload)
        publish(VERIFY_REQUESTED, event_payload)

    return {
        "success": True,
        "message": "Invoice OCR extraction complete",
        "invoice_id": invoice_id,
        "data": extracted,
        "processing_time_seconds": elapsed,
        "patch_result": patch_result,
    }


# ── Run directly with: python -m app.main ──
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("OCR_SERVICE_PORT", "8001"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
