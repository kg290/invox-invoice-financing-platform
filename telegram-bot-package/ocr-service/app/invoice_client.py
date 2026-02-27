"""
invoice_client.py — HTTP client for calling the main InvoX backend.

After OCR extraction, this module:
  1. PATCHes the invoice record with extracted data (mapped to Invoice schema)
  2. Sets ocr_status to 'ocr_done'
"""

import json
import os
from typing import Optional

import httpx

# The main InvoX backend URL (the monolithic FastAPI app)
INVOICE_SERVICE_URL = os.getenv("INVOICE_SERVICE_URL", "http://localhost:8000")

# Timeout for HTTP calls (seconds)
HTTP_TIMEOUT = 30.0


async def patch_invoice_ocr(
    invoice_id: int,
    extracted_data: dict,
    auth_token: Optional[str] = None,
) -> dict:
    """
    PATCH the invoice with OCR-extracted data.
    Maps OCR output fields to the Invoice model schema:
      - buyer_name, buyer_gstin, invoice_date, due_date, grand_total
      - invoice_number (if extracted)
      - ocr_status, ocr_confidence, ocr_raw_text, ocr_warnings
    Calls: PATCH /api/invoices/{invoice_id}/ocr-result
    """
    url = f"{INVOICE_SERVICE_URL}/api/invoices/{invoice_id}/ocr-result"

    # Map OCR output to Invoice model fields
    payload = {
        # OCR metadata
        "ocr_status": "ocr_done",
        "ocr_confidence": extracted_data.get("confidence_score", 0.0),
        "ocr_raw_text": extracted_data.get("raw_text_preview", ""),
        "ocr_warnings": json.dumps(extracted_data.get("warnings", [])),

        # Map to existing Invoice schema fields
        "invoice_number": extracted_data.get("invoice_number"),
        "buyer_name": extracted_data.get("buyer_name"),
        "buyer_gstin": extracted_data.get("buyer_gstin"),
        "invoice_date": extracted_data.get("invoice_date"),
        "due_date": extracted_data.get("due_date"),
        "grand_total": extracted_data.get("total_amount", 0.0),

        # Extra fields the backend can use
        "seller_name": extracted_data.get("seller_name"),
        "seller_gstin": extracted_data.get("seller_gstin"),
        "line_items": extracted_data.get("line_items", []),
    }

    headers = {"Content-Type": "application/json"}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            resp = await client.patch(url, json=payload, headers=headers)
            resp.raise_for_status()
            print(f"  ✅ Invoice #{invoice_id} updated with OCR results (status: ocr_done)")
            return resp.json()
    except httpx.HTTPStatusError as exc:
        print(f"  ❌ Failed to patch invoice #{invoice_id}: {exc.response.status_code} — {exc.response.text}")
        return {"error": str(exc), "status_code": exc.response.status_code}
    except httpx.ConnectError:
        print(f"  ⚠️  Cannot reach invoice service at {INVOICE_SERVICE_URL}")
        return {"error": "Invoice service unreachable"}
    except Exception as exc:
        print(f"  ❌ Unexpected error patching invoice: {exc}")
        return {"error": str(exc)}


async def get_invoice(invoice_id: int, auth_token: Optional[str] = None) -> Optional[dict]:
    """
    GET an invoice by ID from the main backend.
    Calls: GET /api/invoices/{invoice_id}
    """
    url = f"{INVOICE_SERVICE_URL}/api/invoices/{invoice_id}"

    headers = {}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            return resp.json()
    except Exception as exc:
        print(f"  ⚠️  Could not fetch invoice #{invoice_id}: {exc}")
        return None
