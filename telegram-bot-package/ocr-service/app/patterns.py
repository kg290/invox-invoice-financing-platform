"""
patterns.py — Regex patterns and heuristic helpers for Indian invoice field extraction.

Covers:
  - GSTIN (15-char alphanumeric, state code prefix)
  - Invoice numbers
  - Indian date formats (DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD)
  - Indian currency amounts (₹ / Rs / INR with commas)
  - Line item rows
"""

import re
from typing import Optional

# ═══════════════════════════════════════════════
#  GSTIN — 15-character Indian GST Identification Number
#  Format: 2-digit state code + 10-char PAN + 1 entity + 1 check digit + Z
#  Example: 27AAPFU0939F1ZV
# ═══════════════════════════════════════════════
GSTIN_PATTERN = re.compile(
    r"\b\d{2}[A-Z]{5}\d{4}[A-Z]\d[A-Z\d][A-Z]\b",
    re.IGNORECASE
)


# ═══════════════════════════════════════════════
#  Invoice Number — common prefixes: INV, INVOICE, BILL, #
# ═══════════════════════════════════════════════
INVOICE_NUMBER_PATTERNS = [
    re.compile(r"(?:Invoice\s*(?:No|Number|#|Num)\.?\s*[:\-]?\s*)([A-Z0-9\-/]+)", re.IGNORECASE),
    re.compile(r"(?:Bill\s*(?:No|Number|#)\.?\s*[:\-]?\s*)([A-Z0-9\-/]+)", re.IGNORECASE),
    re.compile(r"(?:Inv\.?\s*(?:No|#)\.?\s*[:\-]?\s*)([A-Z0-9\-/]+)", re.IGNORECASE),
    re.compile(r"\b(INV[\-/]?\d{3,}[\-/]?\d*)\b", re.IGNORECASE),
]


# ═══════════════════════════════════════════════
#  Dates — DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY, YYYY-MM-DD
# ═══════════════════════════════════════════════
DATE_PATTERNS = [
    # DD/MM/YYYY or DD-MM-YYYY or DD.MM.YYYY
    re.compile(r"\b(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})\b"),
    # YYYY-MM-DD
    re.compile(r"\b(\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2})\b"),
    # Written format: 25 Feb 2026, February 25, 2026
    re.compile(r"\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{2,4})\b", re.IGNORECASE),
    re.compile(r"\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{2,4})\b", re.IGNORECASE),
]

# Labelled date patterns for invoice_date vs due_date
INVOICE_DATE_LABEL = re.compile(
    r"(?:Invoice\s*Date|Date\s*of\s*Invoice|Inv\.?\s*Date|Bill\s*Date|Date)\s*[:\-]?\s*",
    re.IGNORECASE
)
DUE_DATE_LABEL = re.compile(
    r"(?:Due\s*Date|Payment\s*Due|Pay\s*By|Due\s*On|Exp(?:iry)?\s*Date)\s*[:\-]?\s*",
    re.IGNORECASE
)


# ═══════════════════════════════════════════════
#  Indian Currency Amounts — ₹ 1,23,456.78 / Rs. 1,23,456 / INR 45,000.00
# ═══════════════════════════════════════════════
AMOUNT_PATTERN = re.compile(
    r"(?:₹|Rs\.?|INR)\s*([\d,]+\.?\d*)",
    re.IGNORECASE
)

# Grand total / total amount label
TOTAL_LABEL = re.compile(
    r"(?:Grand\s*Total|Total\s*Amount|Net\s*(?:Amount|Payable)|Amount\s*(?:Due|Payable)|Total\s*(?:Rs|₹|INR)?)\s*[:\-]?\s*",
    re.IGNORECASE
)

# Generic number with Indian comma format: 1,23,456.78
INDIAN_NUMBER = re.compile(r"\b(\d{1,2}(?:,\d{2})*(?:,\d{3})(?:\.\d{1,2})?|\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)\b")


# ═══════════════════════════════════════════════
#  Seller / Buyer Name labels
# ═══════════════════════════════════════════════
SELLER_NAME_LABELS = [
    re.compile(r"(?:Sold\s*By|Seller|From|Supplier|Vendor|Company\s*Name)\s*[:\-]?\s*(.+)", re.IGNORECASE),
]
BUYER_NAME_LABELS = [
    re.compile(r"(?:Bill\s*To|Sold\s*To|Buyer|Ship\s*To|Customer|Billed\s*To)\s*[:\-]?\s*(.+)", re.IGNORECASE),
]


# ═══════════════════════════════════════════════
#  Line Items — tries to match rows like:
#  1  Widget A  10  NOS  500.00  5000.00
# ═══════════════════════════════════════════════
LINE_ITEM_PATTERN = re.compile(
    r"(\d+)\s+"                          # serial / item number
    r"(.+?)\s+"                          # description (lazy)
    r"(\d+(?:\.\d+)?)\s+"               # quantity
    r"([A-Z]{2,5})\s+"                  # unit (NOS, KGS, PCS…)
    r"([\d,]+\.?\d*)\s+"                # unit_price
    r"([\d,]+\.?\d*)",                  # total
    re.IGNORECASE
)

# Alternate simpler pattern: just numbers separated by whitespace
LINE_ITEM_SIMPLE = re.compile(
    r"(.{5,40}?)\s+"                    # description (5-40 chars)
    r"(\d+(?:\.\d+)?)\s+"              # quantity
    r"([\d,]+\.?\d*)\s+"               # unit_price
    r"([\d,]+\.?\d*)",                 # total
    re.IGNORECASE
)


# ═══════════════════════════════════════════════
#  Utility Helpers
# ═══════════════════════════════════════════════

def parse_indian_number(text: str) -> Optional[float]:
    """Convert an Indian-formatted number string '1,23,456.78' to a float."""
    if not text:
        return None
    try:
        cleaned = text.replace(",", "").strip()
        return float(cleaned)
    except ValueError:
        return None


def extract_all_gstins(text: str) -> list[str]:
    """Find all GSTIN numbers in the given text."""
    return GSTIN_PATTERN.findall(text.upper())


def extract_labelled_date(text: str, label_pattern: re.Pattern) -> Optional[str]:
    """
    Find a date that appears immediately after a label like 'Invoice Date:'.
    Returns the raw date string or None.
    """
    for line in text.split("\n"):
        label_match = label_pattern.search(line)
        if label_match:
            rest = line[label_match.end():]
            for dp in DATE_PATTERNS:
                dm = dp.search(rest)
                if dm:
                    return dm.group(1).strip()
    return None


def extract_first_date(text: str) -> Optional[str]:
    """Find the first date-like string in the text."""
    for dp in DATE_PATTERNS:
        m = dp.search(text)
        if m:
            return m.group(1).strip()
    return None
