"""
extractor.py — Google Cloud Vision OCR + structured field extraction for Indian invoices.

Replaces Tesseract with Google Cloud Vision API for higher accuracy.
Uses the service account key from kg-hackathon-b81a207e09b0.json.
"""

import os
import re
from typing import Optional
from pathlib import Path

from google.cloud import vision

from app.patterns import (
    GSTIN_PATTERN,
    INVOICE_NUMBER_PATTERNS,
    INVOICE_DATE_LABEL,
    DUE_DATE_LABEL,
    DATE_PATTERNS,
    AMOUNT_PATTERN,
    TOTAL_LABEL,
    INDIAN_NUMBER,
    SELLER_NAME_LABELS,
    BUYER_NAME_LABELS,
    LINE_ITEM_PATTERN,
    LINE_ITEM_SIMPLE,
    parse_indian_number,
    extract_all_gstins,
    extract_labelled_date,
    extract_first_date,
)


# ── Google Cloud Vision client ──
# Set credentials path — look for key file in multiple locations
_KEY_LOCATIONS = [
    Path(__file__).parent.parent / "kg-hackathon-b81a207e09b0.json",
    Path(__file__).parent.parent.parent.parent / "backend" / "kg-hackathon-b81a207e09b0.json",
]

for _key_path in _KEY_LOCATIONS:
    if _key_path.exists():
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(_key_path)
        print(f"  🔑 Using Vision API key: {_key_path.name}")
        break

_vision_client = None


def _get_vision_client() -> vision.ImageAnnotatorClient:
    """Lazily initialize the Vision API client."""
    global _vision_client
    if _vision_client is None:
        _vision_client = vision.ImageAnnotatorClient()
    return _vision_client


def ocr_image_bytes(image_bytes: bytes) -> str:
    """Run Google Cloud Vision OCR on raw image bytes and return extracted text."""
    client = _get_vision_client()
    image = vision.Image(content=image_bytes)

    response = client.text_detection(image=image)

    if response.error.message:
        raise RuntimeError(f"Vision API error: {response.error.message}")

    texts = response.text_annotations
    if not texts:
        return ""

    # First annotation contains the full text
    return texts[0].description


def ocr_image(img) -> str:
    """Run Vision OCR on a preprocessed numpy image array."""
    import cv2
    # Encode numpy array to PNG bytes
    success, buf = cv2.imencode(".png", img)
    if not success:
        raise ValueError("Failed to encode image to PNG")
    return ocr_image_bytes(buf.tobytes())


def ocr_images(images: list) -> str:
    """Run OCR on multiple images (pages) and concatenate text."""
    pages = []
    for i, img in enumerate(images):
        print(f"  🔍 Running Google Vision OCR on page {i + 1}...")
        text = ocr_image(img)
        pages.append(text)
    return "\n\n--- PAGE BREAK ---\n\n".join(pages)


# ═══════════════════════════════════════════════
#  Field Extraction Functions
# ═══════════════════════════════════════════════

def _extract_invoice_number(text: str) -> Optional[str]:
    """Extract invoice number using labelled patterns."""
    for pattern in INVOICE_NUMBER_PATTERNS:
        m = pattern.search(text)
        if m:
            return m.group(1).strip()
    return None


def _extract_gstins(text: str) -> tuple[Optional[str], Optional[str]]:
    """
    Extract seller and buyer GSTIN.
    Heuristic: first GSTIN found is usually the seller's,
    second is the buyer's.
    """
    gstins = extract_all_gstins(text)
    seen = set()
    unique = []
    for g in gstins:
        gu = g.upper()
        if gu not in seen:
            seen.add(gu)
            unique.append(gu)

    seller_gstin = unique[0] if len(unique) >= 1 else None
    buyer_gstin = unique[1] if len(unique) >= 2 else None
    return seller_gstin, buyer_gstin


def _extract_name(text: str, label_patterns: list[re.Pattern]) -> Optional[str]:
    """Extract a name (seller or buyer) using labelled patterns."""
    for pattern in label_patterns:
        m = pattern.search(text)
        if m:
            name = m.group(1).strip()
            name = name.split("\n")[0].strip()
            name = re.sub(r"[:\-|]$", "", name).strip()
            if len(name) > 2:
                return name
    return None


def _extract_invoice_date(text: str) -> Optional[str]:
    """Extract invoice date using labelled pattern, then fallback to first date."""
    labelled = extract_labelled_date(text, INVOICE_DATE_LABEL)
    if labelled:
        return labelled
    return extract_first_date(text)


def _extract_due_date(text: str) -> Optional[str]:
    """Extract due date using labelled pattern."""
    return extract_labelled_date(text, DUE_DATE_LABEL)


def _extract_total_amount(text: str) -> Optional[float]:
    """
    Extract the grand total / net payable amount.
    Strategy: find 'Total' label → look for amount on the same line or next line.
    Fallback: find the largest currency amount in the document.
    """
    for line in text.split("\n"):
        if TOTAL_LABEL.search(line):
            am = AMOUNT_PATTERN.search(line)
            if am:
                val = parse_indian_number(am.group(1))
                if val and val > 0:
                    return val
            nm = INDIAN_NUMBER.search(line[TOTAL_LABEL.search(line).end():])
            if nm:
                val = parse_indian_number(nm.group(1))
                if val and val > 0:
                    return val

    amounts = []
    for m in AMOUNT_PATTERN.finditer(text):
        val = parse_indian_number(m.group(1))
        if val and val > 0:
            amounts.append(val)

    if amounts:
        return max(amounts)

    return None


def _extract_line_items(text: str) -> list[dict]:
    """Extract line items from the invoice text."""
    items = []

    for m in LINE_ITEM_PATTERN.finditer(text):
        try:
            item = {
                "description": m.group(2).strip(),
                "quantity": float(m.group(3)),
                "unit_price": parse_indian_number(m.group(5)) or 0.0,
                "total": parse_indian_number(m.group(6)) or 0.0,
            }
            if item["description"] and item["total"] > 0:
                items.append(item)
        except (ValueError, IndexError):
            continue

    if items:
        return items

    for m in LINE_ITEM_SIMPLE.finditer(text):
        try:
            item = {
                "description": m.group(1).strip(),
                "quantity": float(m.group(2)),
                "unit_price": parse_indian_number(m.group(3)) or 0.0,
                "total": parse_indian_number(m.group(4)) or 0.0,
            }
            if item["description"] and item["total"] > 0:
                items.append(item)
        except (ValueError, IndexError):
            continue

    return items


# ═══════════════════════════════════════════════
#  Main Extraction Orchestrator
# ═══════════════════════════════════════════════

def extract_invoice_data(raw_text: str) -> dict:
    """
    Parse raw OCR text into structured invoice fields.
    Returns a dict with all extracted fields plus metadata.
    """
    warnings = []

    invoice_number = _extract_invoice_number(raw_text)
    if not invoice_number:
        invoice_number = "UNKNOWN-001"
        warnings.append("invoice_number: Could not extract — using fallback")

    seller_gstin, buyer_gstin = _extract_gstins(raw_text)
    if not seller_gstin:
        warnings.append("seller_gstin: Not found in document")
    if not buyer_gstin:
        warnings.append("buyer_gstin: Not found in document")

    seller_name = _extract_name(raw_text, SELLER_NAME_LABELS)
    if not seller_name:
        seller_name = "Unknown Seller"
        warnings.append("seller_name: Could not extract — using fallback")

    buyer_name = _extract_name(raw_text, BUYER_NAME_LABELS)
    if not buyer_name:
        buyer_name = "Unknown Buyer"
        warnings.append("buyer_name: Could not extract — using fallback")

    invoice_date = _extract_invoice_date(raw_text)
    if not invoice_date:
        warnings.append("invoice_date: Not found in document")

    due_date = _extract_due_date(raw_text)
    if not due_date:
        warnings.append("due_date: Not found in document")

    total_amount = _extract_total_amount(raw_text)
    if not total_amount:
        total_amount = 0.0
        warnings.append("total_amount: Could not extract — set to 0.0")

    line_items = _extract_line_items(raw_text)
    if not line_items:
        warnings.append("line_items: No line items extracted")

    key_fields = [
        invoice_number != "UNKNOWN-001",
        seller_gstin is not None,
        buyer_gstin is not None,
        seller_name != "Unknown Seller",
        buyer_name != "Unknown Buyer",
        invoice_date is not None,
        due_date is not None,
        total_amount > 0,
        len(line_items) > 0,
    ]
    confidence_score = round(sum(key_fields) / len(key_fields), 2)

    return {
        "invoice_number": invoice_number,
        "seller_gstin": seller_gstin,
        "buyer_gstin": buyer_gstin,
        "seller_name": seller_name,
        "buyer_name": buyer_name,
        "invoice_date": invoice_date,
        "due_date": due_date,
        "total_amount": total_amount,
        "line_items": line_items,
        "confidence_score": confidence_score,
        "raw_text_length": len(raw_text),
        "warnings": warnings,
    }
