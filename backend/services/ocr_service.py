"""
OCR Service — Google Cloud Vision API for invoice text extraction.

Uses the service account key (kg-hackathon-b81a207e09b0.json) in the backend folder.
Focused on extracting: invoice pricing, line items, and customer/buyer data.
"""
import os
import re
import io
import json
import logging
from typing import Optional
from pathlib import Path
from datetime import datetime

from google.cloud import vision
from sqlalchemy.orm import Session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("OCRService")

# ── Set Google credentials ──
_KEY_LOCATIONS = [
    Path(__file__).parent.parent / "kg-hackathon-b81a207e09b0.json",
    Path(__file__).parent.parent.parent / "backend" / "kg-hackathon-b81a207e09b0.json",
]

for _key_path in _KEY_LOCATIONS:
    if _key_path.exists():
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(_key_path)
        logger.info(f"Using Vision API key: {_key_path.name}")
        break

_vision_client = None


def _get_vision_client() -> vision.ImageAnnotatorClient:
    global _vision_client
    if _vision_client is None:
        _vision_client = vision.ImageAnnotatorClient()
    return _vision_client


# ═══════════════════════════════════════════════
#  CORE OCR FUNCTION
# ═══════════════════════════════════════════════

def ocr_file_bytes(file_bytes: bytes, is_pdf: bool = False) -> str:
    """Run Google Cloud Vision OCR on raw file bytes."""
    client = _get_vision_client()
    image = vision.Image(content=file_bytes)

    if is_pdf:
        response = client.document_text_detection(image=image)
    else:
        response = client.text_detection(image=image)

    if response.error.message:
        raise RuntimeError(f"Vision API error: {response.error.message}")

    texts = response.text_annotations
    if not texts:
        return ""

    return texts[0].description


# ═══════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════

GSTIN_RE = re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z]\d[A-Z\d][A-Z]\b", re.IGNORECASE)


def _parse_num(s: str) -> Optional[float]:
    """Parse an Indian-format number like 11,480.00 or 5,714.29"""
    if not s:
        return None
    try:
        return float(s.replace(",", "").strip())
    except ValueError:
        return None


def _normalize_date(ds: str) -> Optional[str]:
    """Try many date formats common in Indian invoices."""
    if not ds:
        return None
    ds = ds.strip()
    fmts = [
        "%d-%b-%y", "%d-%b-%Y",          # 19-Feb-26, 19-Feb-2026
        "%d %b %y", "%d %b %Y",          # 19 Feb 26, 19 Feb 2026
        "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",  # 19/02/2026
        "%d/%m/%y", "%d-%m-%y",           # 19/02/26
        "%Y-%m-%d", "%Y/%m/%d",           # 2026-02-19
        "%b %d, %Y", "%B %d, %Y",        # Feb 19, 2026
        "%d %B %Y",                        # 19 February 2026
    ]
    for fmt in fmts:
        try:
            return datetime.strptime(ds, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return ds


def _lines(text: str) -> list[str]:
    return [l.strip() for l in text.split("\n") if l.strip()]


# ═══════════════════════════════════════════════
#  EXTRACTION — focused on pricing + customer
# ═══════════════════════════════════════════════

def _find_value_near_label(text: str, label_re, value_re, max_lines_ahead: int = 5) -> Optional[str]:
    """
    Find a label in the text, then search the same line and the next N lines
    for the value pattern. Handles OCR splitting label and value across lines.
    """
    lines = _lines(text)
    for i, line in enumerate(lines):
        if label_re.search(line):
            # Check same line first (after label)
            after_label = label_re.sub("", line).strip()
            m = value_re.search(after_label)
            if m:
                return m.group(1).strip() if m.lastindex else m.group(0).strip()
            # Check subsequent lines
            for j in range(i + 1, min(i + 1 + max_lines_ahead, len(lines))):
                m = value_re.search(lines[j])
                if m:
                    return m.group(1).strip() if m.lastindex else m.group(0).strip()
    return None


def _extract_invoice_number(text: str) -> Optional[str]:
    """Extract invoice number — handles label:value on same or different lines.
    Prefers short numeric values over long alphanumeric codes."""
    lines = _lines(text)
    label_re = re.compile(r"Invoice\s*(?:No|Number|#|Num)\.?", re.IGNORECASE)
    label_words = {"invoice", "no", "number", "dt", "date", "bill", "hsn", "batch", "exp"}

    for i, line in enumerate(lines):
        if label_re.search(line):
            # Same line: look for colon + number
            m = re.search(r":\s*([A-Z0-9][\w\-/]{1,20})", line, re.IGNORECASE)
            if m and m.group(1).lower() not in label_words:
                return m.group(1).strip()

            # Collect all colon-prefixed candidates and standalone numbers
            candidates = []
            for j in range(i + 1, min(i + 15, len(lines))):
                nxt = lines[j].strip()
                # Colon-prefixed value like ": 17014" or ": INV-123"
                m = re.match(r"^:\s*([A-Z0-9][\w\-/]{1,20})$", nxt, re.IGNORECASE)
                if m and m.group(1).lower() not in label_words:
                    candidates.append(m.group(1).strip())
                # Standalone number/code on its own line
                m = re.match(r"^([A-Z]{0,3}\d{3,15}[\-/]?\d{0,5})$", nxt, re.IGNORECASE)
                if m and m.group(1).lower() not in label_words:
                    candidates.append(m.group(1).strip())

            if candidates:
                # Prefer purely numeric, short values (typical invoice numbers)
                numeric = [c for c in candidates if re.match(r"^\d{1,15}$", c)]
                if numeric:
                    return numeric[0]
                # Then short alphanumeric (< 12 chars, not license-like)
                short = [c for c in candidates if len(c) <= 12 and not c.startswith("LC")]
                if short:
                    return short[0]
                return candidates[0]

    # Fallback: Bill No
    bill_re = re.compile(r"Bill\s*(?:No|Number|#)\.?\s*[:\-]?\s*([A-Z0-9][\w\-/]{1,20})", re.IGNORECASE)
    m = bill_re.search(text)
    if m and m.group(1).lower() not in label_words:
        return m.group(1).strip()

    return None


def _extract_invoice_date(text: str) -> Optional[str]:
    """Extract invoice date — handles multi-line label:value.
    Prefers standalone date lines over dates embedded in HSN/batch rows."""
    lines = _lines(text)
    label_re = re.compile(r"Invoice\s*(?:Date|Dt)\.?", re.IGNORECASE)
    date_re = re.compile(
        r"(\d{1,2}[\-/\.]\w{3,9}[\-/\.]\d{2,4}|\d{1,2}[\-/\.]\d{1,2}[\-/\.]\d{2,4}|\d{4}[\-/\.]\d{1,2}[\-/\.]\d{1,2})"
    )

    for i, line in enumerate(lines):
        if label_re.search(line):
            # Same line after label
            rest = label_re.sub("", line).strip()
            m = date_re.search(rest)
            if m:
                return _normalize_date(m.group(1))
            # Search subsequent lines — expand window to 25 lines for
            # column-based OCR layouts where labels and values are far apart
            for j in range(i + 1, min(i + 25, len(lines))):
                nxt = lines[j].strip()
                m = date_re.search(nxt)
                if m:
                    # Skip lines with HSN codes (start with 4+ digits followed by more data)
                    if re.match(r"^\d{4,}\s", nxt):
                        continue
                    # Skip batch/expiry dates (lines containing "batch" or "exp")
                    if re.search(r"batch|exp\b", nxt, re.IGNORECASE):
                        continue
                    # For colon-prefixed value lines (typical in column-based OCR),
                    # accept if it's a clean date
                    clean = nxt.lstrip(": ").strip()
                    m2 = date_re.match(clean)
                    if m2:
                        return _normalize_date(m2.group(1))
                    # Also accept inline dates not on HSN rows
                    return _normalize_date(m.group(1))

    # Fallback: Bill Date
    label2 = re.compile(r"Bill\s*Date|Date\s*of\s*Invoice", re.IGNORECASE)
    for i, line in enumerate(lines):
        if label2.search(line):
            rest = label2.sub("", line).strip()
            m = date_re.search(rest)
            if m:
                return _normalize_date(m.group(1))
            for j in range(i + 1, min(i + 15, len(lines))):
                m = date_re.search(lines[j])
                if m:
                    return _normalize_date(m.group(1))

    return None


# Keywords that disqualify a line from being a buyer name
_NAME_EXCLUDE_KWS = [
    "invoice", "date", "no.", "gst", "license", "phone", "email",
    "address", "tax", "sr.", "description", "discription", "particulars",
    "hsn", "qty", "rate", "amount", "batch", "exp", "bank", "ifsc",
    "cgst", "sgst", "igst", "cess", "round", "total", "subject",
    "receiver", "seal", "signature", "m/s", "for:", "we declare",
    "jurisdiction", "in-words", "current a/c", "our bank",
]


def _is_name_candidate(line: str, seller_name: str = "") -> bool:
    """Check if a line looks like a person/company name."""
    c = line.strip()
    if len(c) < 3 or len(c) > 60:
        return False
    if re.match(r"^[:\-\.\d]", c):          # starts with :, -, digit, dot
        return False
    if re.match(r"^\d+$", c):                 # purely numeric
        return False
    if not re.search(r"[A-Za-z]{2,}", c):     # must contain letters
        return False
    if GSTIN_RE.search(c):                     # GSTIN
        return False
    low = c.lower()
    if any(kw in low for kw in _NAME_EXCLUDE_KWS):
        return False
    # Don't pick the seller name again
    if seller_name and low == seller_name.lower():
        return False
    return True


def _extract_buyer_name(text: str, seller_name: str = "") -> Optional[str]:
    """
    Extract buyer/customer name. In Indian invoices this is often:
    - After a label like "Bill To", "Sold To", "Buyer", "Customer"
    - Or a standalone name line right before the items table
    - Or identifiable by looking backwards from the table header
    """
    lines = _lines(text)

    # ── Strategy 1: Labelled buyer ──
    buyer_labels = re.compile(
        r"(?:Bill\s*To|Sold\s*To|Buyer|Ship\s*To|Customer|Billed\s*To|Consignee|Recipient|M/s\.?)\s*[:\-]?\s*",
        re.IGNORECASE,
    )
    for i, line in enumerate(lines):
        m = buyer_labels.search(line)
        if m:
            after = line[m.end():].strip()
            if after and len(after) > 2 and _is_name_candidate(after, seller_name):
                return re.sub(r"[:\-|]$", "", after).strip()
            if i + 1 < len(lines):
                nxt = lines[i + 1].strip()
                if _is_name_candidate(nxt, seller_name):
                    return nxt

    # ── Locate table start ──
    table_start_markers = ["sr.", "description", "discription", "particulars", "item",
                           "sl.", "s.no", "hsn", "qty"]
    table_start_idx = len(lines)
    for i, line in enumerate(lines):
        if any(mk in line.lower() for mk in table_start_markers):
            table_start_idx = i
            break

    # ── Strategy 2 (backwards from table): most reliable for Indian invoices ──
    # The buyer name typically appears 1-5 lines BEFORE the table header.
    # Walk backwards from table_start, skipping place-name single words
    # (city/town names like "RANZANI") and look for a multi-word name.
    for i in range(table_start_idx - 1, max(0, table_start_idx - 8), -1):
        candidate = lines[i].strip()
        if not _is_name_candidate(candidate, seller_name):
            continue
        # Prefer multi-word candidates ("ARJUN PATIL") over single-word
        words = candidate.split()
        if len(words) >= 2 and all(w[0].isupper() for w in words if w.isalpha()):
            return candidate
    # If no multi-word found, accept single-word name near table start
    for i in range(table_start_idx - 1, max(0, table_start_idx - 5), -1):
        candidate = lines[i].strip()
        if _is_name_candidate(candidate, seller_name) and len(candidate.split()) == 1:
            return candidate

    # ── Strategy 3 (forward scan): search between seller block and table ──
    seller_end_idx = 0
    seller_kws = ["phone", "email", "e-mail", "mob", "fax", "tel", "tax invoice",
                   "gstin", "gst no", "dist.", "tal."]
    for i, line in enumerate(lines[:min(15, table_start_idx)]):
        if any(kw in line.lower() for kw in seller_kws):
            seller_end_idx = max(seller_end_idx, i)

    # Scan all lines from seller end to table start (not just +6)
    for i in range(seller_end_idx + 1, table_start_idx):
        candidate = lines[i].strip()
        if _is_name_candidate(candidate, seller_name):
            words = candidate.split()
            if len(words) >= 2:
                return candidate

    return None


def _extract_seller_name(text: str) -> Optional[str]:
    """Extract seller/vendor name — usually the first prominent line."""
    lines = _lines(text)
    skip = ["tax invoice", "invoice", "gst", "date", "phone", "email", "no.",
            "bill", "receipt", "estimate"]
    for line in lines[:5]:
        if len(line) > 3 and not any(kw in line.lower() for kw in skip):
            if re.match(r'^[A-Z]', line) and len(line) < 80:
                return line
    return None


def _extract_total_amount(text: str) -> Optional[float]:
    """
    Extract the grand total / final amount. Strategies (in priority order):
    1. "Grand Total" / "Total Amount" label nearby (most reliable)
    2. ₹/Rs prefix with the largest value (min ₹50 threshold)
    3. "In-Words" line mentions the amount
    4. Largest amount in the document
    """
    lines = _lines(text)
    number_re = re.compile(r"[\d,]+\.\d{2}")

    # Strategy 1 (HIGHEST PRIORITY): "Total Amount" / "Grand Total" label — look for number nearby
    total_label = re.compile(
        r"Grand\s*Total|Total\s*Amount|Net\s*(?:Amount|Payable)|Amount\s*(Due|Payable)|Bill\s*Amount",
        re.IGNORECASE,
    )
    # Match decimal amounts like 3,663.20 OR integer amounts like 3,663 or 3663
    amount_re = re.compile(r"([\d,]+\.\d{1,2}|\b[\d,]{3,10}\b)")
    for i, line in enumerate(lines):
        if total_label.search(line):
            # Same line — strip the label text first
            rest = total_label.sub("", line).strip()
            m = amount_re.search(rest)
            if m:
                v = _parse_num(m.group(1))
                if v and 10 < v < 10_000_000:  # Cap at 1 crore for sanity
                    return v
            # Next few lines
            for j in range(i + 1, min(i + 4, len(lines))):
                m = amount_re.search(lines[j])
                if m:
                    v = _parse_num(m.group(1))
                    if v and 10 < v < 10_000_000:
                        return v

    # Strategy 2: Find ₹ / Rs. prefixed amounts — take the largest (min threshold ₹50)
    rupee_amounts = []
    for m in re.finditer(r"(?:₹|Rs\.?|INR)\s*([\d,]+\.?\d*)", text, re.IGNORECASE):
        v = _parse_num(m.group(1))
        if v and v > 50:
            rupee_amounts.append(v)
    if rupee_amounts:
        return max(rupee_amounts)

    # Strategy 3: "In-Words" line sometimes has the amount nearby
    for i, line in enumerate(lines):
        if "in-words" in line.lower() or "in words" in line.lower():
            # Check nearby lines for a big number
            for j in range(max(0, i - 3), min(i + 4, len(lines))):
                m = number_re.search(lines[j])
                if m:
                    v = _parse_num(m.group(0))
                    if v and v > 100:
                        return v

    # Strategy 4: Fallback — find all decimal numbers and return the largest
    all_amounts = []
    for m in number_re.finditer(text):
        v = _parse_num(m.group(0))
        if v and v > 10:
            all_amounts.append(v)
    if all_amounts:
        return max(all_amounts)

    return None


def _extract_line_items(text: str) -> list[dict]:
    """
    Extract line items from Indian invoice OCR text.
    Handles the common case where OCR splits table columns into separate text blocks.

    Strategy:
    1. Find numbered product descriptions (1 ProductName, 2 ProductName...)
    2. Find HSN codes (4-8 digit codes near descriptions)
    3. Find qty + rate rows (4 Nos 635.59...)
    4. Find amounts column values
    5. Correlate by order
    """
    lines = _lines(text)

    # ── Find product descriptions ──
    # Pattern: Sr.No followed by product name, e.g. "1 Natio (100 Gm)"
    desc_re = re.compile(r"^(\d{1,2})\s+([A-Za-z].{2,60})$")
    # Unit words that indicate a qty/rate row, not a description
    unit_words = re.compile(r"^(?:Nos|Pcs|Kg|Ltr|Box|Bag|Set|Unit|Btl|Pkt)\b", re.IGNORECASE)
    descriptions = []
    for line in lines:
        m = desc_re.match(line)
        if m:
            sr = int(m.group(1))
            desc = m.group(2).strip()
            # Filter out noise: qty/rate rows, dates, HSN codes, labels
            if (not unit_words.match(desc) and
                    not re.match(r"^\d{4,}$", desc) and
                    not re.match(r"^\d+[\-/\.]\d+[\-/\.]\d+$", desc) and
                    "invoice" not in desc.lower() and "license" not in desc.lower()):
                descriptions.append({"sr": sr, "description": desc})

    # ── Find HSN codes ──
    # Pattern: standalone 4-8 digit codes that appear in a column
    hsn_re = re.compile(r"^(\d{4,8})$")
    hsn_codes = []
    for line in lines:
        m = hsn_re.match(line.strip())
        if m:
            code = m.group(1)
            # Filter out years (2024-2030) and very small numbers
            if not (2000 <= int(code) <= 2030) and len(code) >= 4:
                hsn_codes.append(code)

    # ── Find qty + rate rows ──
    # Pattern: "4 Nos 635.59 18 %" or "1 Nos 5,714.29 5 %"
    # Also handle: "1 NOS 254.24" (without GST %), "3 NOS 118.64 9"
    qty_re = re.compile(r"(\d+)\s*(?:Nos|Pcs|Kg|Ltr|Box|Bag|Set|Unit|Btl|Pkt)\s+([\d,]+\.?\d*)\s*(\d+)?\s*%?", re.IGNORECASE)
    qty_rows = []
    for line in lines:
        m = qty_re.search(line)
        if m:
            gst_pct = float(m.group(3)) if m.group(3) else 0
            qty_rows.append({
                "quantity": float(m.group(1)),
                "base_rate": _parse_num(m.group(2)) or 0.0,
                "gst_percent": gst_pct if gst_pct <= 28 else 0,  # Filter out non-GST numbers
            })

    # ── Find amount column values ──
    # These are standalone decimal numbers like "2,542.36", "576.28" etc.
    # Usually appear after the qty+rate rows
    # We need to find pairs: N.Rate and Amount for each item

    # ── Build items by correlating descriptions with qty/rate rows ──
    items = []
    num_items = max(len(descriptions), len(qty_rows))

    for idx in range(num_items):
        item = {"description": "OCR Item", "quantity": 1, "unit": "NOS",
                "unit_price": 0.0, "gst_rate": 18, "total": 0.0, "hsn_sac_code": "0000"}

        if idx < len(descriptions):
            item["description"] = descriptions[idx]["description"]
        if idx < len(qty_rows):
            item["quantity"] = qty_rows[idx]["quantity"]
            item["unit_price"] = qty_rows[idx]["base_rate"]
            if qty_rows[idx]["gst_percent"] > 0:
                item["gst_rate"] = qty_rows[idx]["gst_percent"]
            item["total"] = qty_rows[idx]["base_rate"] * qty_rows[idx]["quantity"]
        if idx < len(hsn_codes):
            item["hsn_sac_code"] = hsn_codes[idx]

        if item["description"] != "OCR Item" or item["total"] > 0:
            items.append(item)

    return items


def _extract_tax_details(text: str) -> dict:
    """Extract CGST, SGST, IGST values."""
    taxes = {"cgst": 0.0, "sgst": 0.0, "igst": 0.0}
    number_re = re.compile(r"([\d,]+\.\d{2})")
    lines = _lines(text)

    for i, line in enumerate(lines):
        ll = line.lower()
        if "cgst" in ll:
            m = number_re.search(line)
            if not m and i + 1 < len(lines):
                m = number_re.search(lines[i + 1])
            if m:
                taxes["cgst"] = _parse_num(m.group(1)) or 0.0
        elif "sgst" in ll:
            m = number_re.search(line)
            if not m and i + 1 < len(lines):
                m = number_re.search(lines[i + 1])
            if m:
                taxes["sgst"] = _parse_num(m.group(1)) or 0.0
        elif "igst" in ll:
            m = number_re.search(line)
            if not m and i + 1 < len(lines):
                m = number_re.search(lines[i + 1])
            if m:
                taxes["igst"] = _parse_num(m.group(1)) or 0.0

    return taxes


def extract_invoice_data(raw_text: str) -> dict:
    """
    Parse raw OCR text into structured invoice data.
    Focused on: pricing (total + line items + tax) and customer info.
    """
    warnings = []

    # ── Invoice number ──
    invoice_number = _extract_invoice_number(raw_text)
    if not invoice_number:
        invoice_number = "UNKNOWN-001"
        warnings.append("invoice_number: Could not extract")

    # ── GSTIN ──
    gstins = list(set(GSTIN_RE.findall(raw_text.upper())))
    seller_gstin = gstins[0] if len(gstins) >= 1 else None
    buyer_gstin = gstins[1] if len(gstins) >= 2 else None

    # ── Names ──
    seller_name = _extract_seller_name(raw_text) or "Unknown Seller"
    buyer_name = _extract_buyer_name(raw_text, seller_name=seller_name) or "Unknown Buyer"
    if buyer_name == "Unknown Buyer":
        warnings.append("buyer_name: Could not extract")

    # ── Date ──
    invoice_date = _extract_invoice_date(raw_text)
    if not invoice_date:
        warnings.append("invoice_date: Not found")

    # ── Due date ──
    due_date = None
    if invoice_date:
        try:
            from datetime import timedelta
            dt = datetime.strptime(invoice_date, "%Y-%m-%d")
            due_date = (dt + timedelta(days=30)).strftime("%Y-%m-%d")
        except:
            pass

    # ── Pricing ──
    total_amount = _extract_total_amount(raw_text) or 0.0

    line_items = _extract_line_items(raw_text)
    if not line_items:
        warnings.append("line_items: No line items extracted")

    # If total_amount is suspiciously low but we have line items, use sum of line items
    if line_items:
        items_sum = sum(item.get("total", 0) for item in line_items)
        if items_sum > 0 and (total_amount <= 0 or total_amount < items_sum * 0.5):
            total_amount = items_sum
            warnings.append("total_amount: Used line items sum as fallback")

    if total_amount <= 0:
        warnings.append("total_amount: Could not extract")

    taxes = _extract_tax_details(raw_text)

    # ── Confidence ──
    checks = [
        invoice_number != "UNKNOWN-001",
        seller_gstin is not None,
        seller_name != "Unknown Seller",
        buyer_name != "Unknown Buyer",
        invoice_date is not None,
        total_amount > 0,
        len(line_items) > 0,
    ]
    confidence_score = round(sum(checks) / len(checks), 2)

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
        "taxes": taxes,
        "confidence_score": confidence_score,
        "raw_text_length": len(raw_text),
        "warnings": warnings,
    }


# ═══════════════════════════════════════════════
#  MAIN ENTRY POINT: run OCR on a file and update the invoice in DB
# ═══════════════════════════════════════════════

def run_ocr_and_update(invoice_id: int, file_path: str):
    """
    Read a file, OCR it with Google Vision, extract fields,
    and update the invoice record in the database.
    Also sends a Telegram notification to the user who uploaded it.
    Runs synchronously (called from BackgroundTasks).
    """
    from database import SessionLocal
    from models import Invoice, InvoiceItem, User, Notification

    db = SessionLocal()
    try:
        inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not inv:
            logger.error(f"Invoice {invoice_id} not found")
            return

        logger.info(f"Starting OCR for invoice #{invoice_id} — file: {file_path}")

        # Read file
        with open(file_path, "rb") as f:
            file_bytes = f.read()

        is_pdf = file_path.lower().endswith(".pdf")

        # Run OCR
        raw_text = ocr_file_bytes(file_bytes, is_pdf=is_pdf)

        if not raw_text.strip():
            inv.ocr_status = "failed"
            inv.ocr_warnings = json.dumps(["OCR produced no text — image may be blank or unreadable"])
            db.commit()
            logger.warning(f"OCR produced no text for invoice {invoice_id}")
            return

        logger.info(f"OCR extracted {len(raw_text)} characters for invoice #{invoice_id}")

        # Extract fields
        extracted = extract_invoice_data(raw_text)

        # Update invoice
        inv.ocr_status = "ocr_done"
        inv.ocr_confidence = extracted["confidence_score"]
        inv.ocr_raw_text = raw_text[:5000]
        inv.ocr_warnings = json.dumps(extracted["warnings"])

        if extracted["invoice_number"] and extracted["invoice_number"] != "UNKNOWN-001":
            existing = db.query(Invoice).filter(
                Invoice.invoice_number == extracted["invoice_number"],
                Invoice.id != invoice_id
            ).first()
            if not existing:
                inv.invoice_number = extracted["invoice_number"]

        if extracted["buyer_name"] and extracted["buyer_name"] != "Unknown Buyer":
            inv.buyer_name = extracted["buyer_name"]
        if extracted["buyer_gstin"]:
            inv.buyer_gstin = extracted["buyer_gstin"]
        if extracted["invoice_date"]:
            inv.invoice_date = extracted["invoice_date"]
        if extracted["due_date"]:
            inv.due_date = extracted["due_date"]

        # Create line items with proper tax calculation
        supply_type = inv.supply_type or "intra_state"
        subtotal = 0.0
        total_cgst = 0.0
        total_sgst = 0.0
        total_igst = 0.0

        for idx, item_data in enumerate(extracted.get("line_items", [])):
            taxable = item_data.get("total", 0)
            gst_rate = item_data.get("gst_rate", 18)
            gst_amount = round(taxable * gst_rate / 100, 2)

            if supply_type == "intra_state":
                cgst = round(gst_amount / 2, 2)
                sgst = round(gst_amount / 2, 2)
                igst = 0.0
            else:
                cgst = 0.0
                sgst = 0.0
                igst = gst_amount

            item_total = round(taxable + cgst + sgst + igst, 2)

            item = InvoiceItem(
                invoice_id=invoice_id,
                item_number=idx + 1,
                description=item_data.get("description", "OCR Item"),
                hsn_sac_code=item_data.get("hsn_sac_code", "0000"),
                quantity=item_data.get("quantity", 1),
                unit=item_data.get("unit", "NOS"),
                unit_price=item_data.get("unit_price", 0),
                discount_percent=0,
                discount_amount=0,
                taxable_value=taxable,
                gst_rate=gst_rate,
                cgst_amount=cgst,
                sgst_amount=sgst,
                igst_amount=igst,
                cess_rate=0,
                cess_amount=0,
                total_amount=item_total,
            )
            db.add(item)

            subtotal += taxable
            total_cgst += cgst
            total_sgst += sgst
            total_igst += igst

        # Recalculate invoice-level totals from line items
        inv.subtotal = round(subtotal, 2)
        inv.total_cgst = round(total_cgst, 2)
        inv.total_sgst = round(total_sgst, 2)
        inv.total_igst = round(total_igst, 2)
        inv.total_cess = 0.0
        inv.total_discount = 0.0

        # Use extracted grand_total if reasonable, otherwise compute from items
        items_grand = round(subtotal + total_cgst + total_sgst + total_igst, 2)
        extracted_total = extracted["total_amount"] or 0

        # Sanity check: extracted total must be within 2x of line items total
        # to avoid OCR misreads (e.g. account numbers parsed as amounts)
        if (extracted_total > 0 and items_grand > 0
                and 0.5 * items_grand <= extracted_total <= 2.0 * items_grand):
            inv.grand_total = extracted_total
        elif items_grand > 0:
            inv.grand_total = items_grand
        elif extracted_total > 0 and extracted_total < 10_000_000:
            inv.grand_total = extracted_total

        # Round-off is the small difference between exact total and displayed total
        if items_grand > 0:
            diff = round(inv.grand_total - items_grand, 2)
            inv.round_off = diff if abs(diff) < 100 else 0.0
        else:
            inv.round_off = 0.0

        db.commit()

        logger.info(
            f"OCR complete for invoice #{invoice_id}: "
            f"confidence={extracted['confidence_score']}, "
            f"total=₹{extracted['total_amount']}"
        )

        # Send Telegram notification to the uploader
        try:
            user = db.query(User).filter(User.vendor_id == inv.vendor_id).first()
            if user and user.telegram_chat_id:
                from services.telegram_service import send_telegram_message_sync, build_ocr_complete_message
                msg = build_ocr_complete_message(
                    invoice_id=invoice_id,
                    confidence=extracted["confidence_score"],
                    invoice_number=inv.invoice_number,
                    total=extracted["total_amount"],
                )
                send_telegram_message_sync(user.telegram_chat_id, msg)
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")

        # Also create an in-app notification
        try:
            user = db.query(User).filter(User.vendor_id == inv.vendor_id).first()
            if user:
                notif = Notification(
                    user_id=user.id,
                    title="Invoice OCR Complete",
                    message=f"Invoice #{inv.invoice_number} processed. Confidence: {extracted['confidence_score']:.0%}. Total: ₹{extracted['total_amount']:,.2f}",
                    notification_type="system",
                )
                db.add(notif)
                db.commit()
        except Exception as e:
            logger.error(f"Failed to create notification: {e}")

    except Exception as e:
        logger.error(f"OCR failed for invoice {invoice_id}: {e}")
        try:
            inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
            if inv:
                inv.ocr_status = "failed"
                inv.ocr_warnings = json.dumps([str(e)])
                db.commit()
        except:
            pass
    finally:
        db.close()
