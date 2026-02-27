from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from database import get_db
from models import Invoice, InvoiceItem, Vendor, User
from blockchain import add_block, hash_data
from routes.auth import get_current_user
from pdf_generator import generate_invoice_pdf
from services.email_service import email_service

router = APIRouter(prefix="/api/invoices", tags=["invoices"])


# ── State codes for place of supply ──
STATE_CODES = {
    "Andhra Pradesh": "37", "Arunachal Pradesh": "12", "Assam": "18", "Bihar": "10",
    "Chhattisgarh": "22", "Goa": "30", "Gujarat": "24", "Haryana": "06",
    "Himachal Pradesh": "02", "Jharkhand": "20", "Karnataka": "29", "Kerala": "32",
    "Madhya Pradesh": "23", "Maharashtra": "27", "Manipur": "14", "Meghalaya": "17",
    "Mizoram": "15", "Nagaland": "13", "Odisha": "21", "Punjab": "03",
    "Rajasthan": "08", "Sikkim": "11", "Tamil Nadu": "33", "Telangana": "36",
    "Tripura": "16", "Uttar Pradesh": "09", "Uttarakhand": "05", "West Bengal": "19",
    "Andaman and Nicobar Islands": "35", "Chandigarh": "04",
    "Dadra and Nagar Haveli and Daman and Diu": "26", "Delhi": "07",
    "Jammu and Kashmir": "01", "Ladakh": "38", "Lakshadweep": "31", "Puducherry": "34",
}

GST_RATES = [0, 5, 12, 18, 28]
UNITS = ["NOS", "KGS", "LTR", "MTR", "SQM", "SQF", "PCS", "BOX", "SET", "BAG", "TON", "QTL", "DOZ", "PAR", "UNT"]


# ═══════ Schemas ═══════

class InvoiceItemCreate(BaseModel):
    description: str = Field(..., min_length=2)
    hsn_sac_code: str = Field(..., min_length=4, max_length=8)
    quantity: float = Field(..., gt=0)
    unit: str = Field(...)
    unit_price: float = Field(..., ge=0)
    discount_percent: float = Field(default=0, ge=0, le=100)
    gst_rate: float = Field(...)  # 0, 5, 12, 18, 28
    cess_rate: float = Field(default=0, ge=0)


class InvoiceCreate(BaseModel):
    invoice_date: str = Field(...)
    due_date: str = Field(...)
    supply_type: str = Field(...)  # intra_state, inter_state
    place_of_supply: str = Field(...)
    reverse_charge: bool = Field(default=False)

    buyer_name: str = Field(..., min_length=2)
    buyer_gstin: Optional[str] = None
    buyer_address: str = Field(..., min_length=5)
    buyer_city: str = Field(...)
    buyer_state: str = Field(...)
    buyer_pincode: str = Field(..., min_length=6, max_length=6)
    buyer_phone: Optional[str] = None
    buyer_email: Optional[str] = None

    notes: Optional[str] = None
    terms: Optional[str] = None
    payment_status: Optional[str] = Field(default="unpaid")  # "paid" or "unpaid"

    items: List[InvoiceItemCreate] = Field(..., min_length=1)


class InvoiceItemResponse(BaseModel):
    id: int
    item_number: int
    description: str
    hsn_sac_code: str
    quantity: float
    unit: str
    unit_price: float
    discount_percent: float
    discount_amount: float
    taxable_value: float
    gst_rate: float
    cgst_amount: float
    sgst_amount: float
    igst_amount: float
    cess_rate: float
    cess_amount: float
    total_amount: float

    class Config:
        from_attributes = True


class InvoiceResponse(BaseModel):
    id: int
    vendor_id: int
    invoice_number: str
    invoice_date: str
    due_date: str
    supply_type: str
    place_of_supply: str
    place_of_supply_code: str
    reverse_charge: bool
    buyer_name: str
    buyer_gstin: Optional[str]
    buyer_address: str
    buyer_city: str
    buyer_state: str
    buyer_state_code: str
    buyer_pincode: str
    buyer_phone: Optional[str]
    buyer_email: Optional[str]
    subtotal: float
    total_cgst: float
    total_sgst: float
    total_igst: float
    total_cess: float
    total_discount: float
    round_off: float
    grand_total: float
    notes: Optional[str]
    terms: Optional[str]
    invoice_status: str
    payment_status: str
    blockchain_hash: Optional[str]
    block_index: Optional[int]
    is_listed: bool
    items: List[InvoiceItemResponse] = []

    class Config:
        from_attributes = True


class InvoiceListResponse(BaseModel):
    id: int
    vendor_id: int
    invoice_number: str
    invoice_date: str
    due_date: str
    buyer_name: str
    grand_total: float
    invoice_status: str
    payment_status: str
    is_listed: bool
    blockchain_hash: Optional[str]

    class Config:
        from_attributes = True


# ═══════ Helpers ═══════

def _generate_invoice_number(db: Session, vendor_id: int) -> str:
    count = db.query(Invoice).filter(Invoice.vendor_id == vendor_id).count()
    return f"INV-{vendor_id:04d}-{count + 1:05d}"


def _calculate_item(item_data: InvoiceItemCreate, supply_type: str) -> dict:
    """Calculate all tax fields for a single line item."""
    gross = item_data.quantity * item_data.unit_price
    discount_amount = round(gross * item_data.discount_percent / 100, 2)
    taxable_value = round(gross - discount_amount, 2)

    gst_amount = round(taxable_value * item_data.gst_rate / 100, 2)

    if supply_type == "intra_state":
        cgst = round(gst_amount / 2, 2)
        sgst = round(gst_amount / 2, 2)
        igst = 0.0
    else:
        cgst = 0.0
        sgst = 0.0
        igst = gst_amount

    cess_amount = round(taxable_value * item_data.cess_rate / 100, 2)
    total = round(taxable_value + cgst + sgst + igst + cess_amount, 2)

    return {
        "discount_amount": discount_amount,
        "taxable_value": taxable_value,
        "cgst_amount": cgst,
        "sgst_amount": sgst,
        "igst_amount": igst,
        "cess_amount": cess_amount,
        "total_amount": total,
    }


# ═══════ Endpoints ═══════

@router.post("/vendor/{vendor_id}", response_model=InvoiceResponse, status_code=201)
def create_invoice(vendor_id: int, data: InvoiceCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Create a new GST-compliant invoice with automatic tax calculation and blockchain recording."""

    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    # Validate GST rate
    for item in data.items:
        if item.gst_rate not in GST_RATES:
            raise HTTPException(status_code=400, detail=f"Invalid GST rate {item.gst_rate}%. Must be one of {GST_RATES}")
        if item.unit not in UNITS:
            raise HTTPException(status_code=400, detail=f"Invalid unit '{item.unit}'. Must be one of {UNITS}")

    # Resolve state codes
    pos_code = STATE_CODES.get(data.place_of_supply, "00")
    buyer_state_code = STATE_CODES.get(data.buyer_state, "00")

    # Validate payment_status
    if data.payment_status not in ("paid", "unpaid"):
        raise HTTPException(status_code=400, detail="payment_status must be 'paid' or 'unpaid'")

    invoice_number = _generate_invoice_number(db, vendor_id)

    # Create invoice
    invoice = Invoice(
        vendor_id=vendor_id,
        invoice_number=invoice_number,
        invoice_date=data.invoice_date,
        due_date=data.due_date,
        supply_type=data.supply_type,
        place_of_supply=data.place_of_supply,
        place_of_supply_code=pos_code,
        reverse_charge=data.reverse_charge,
        buyer_name=data.buyer_name,
        buyer_gstin=data.buyer_gstin,
        buyer_address=data.buyer_address,
        buyer_city=data.buyer_city,
        buyer_state=data.buyer_state,
        buyer_state_code=buyer_state_code,
        buyer_pincode=data.buyer_pincode,
        buyer_phone=data.buyer_phone,
        buyer_email=data.buyer_email,
        notes=data.notes,
        terms=data.terms,
        invoice_status="issued",
        payment_status=data.payment_status,
    )
    db.add(invoice)
    db.flush()  # get invoice.id

    # Process items
    total_subtotal = 0
    total_cgst = 0
    total_sgst = 0
    total_igst = 0
    total_cess = 0
    total_discount = 0

    for idx, item_data in enumerate(data.items, 1):
        calc = _calculate_item(item_data, data.supply_type)
        item = InvoiceItem(
            invoice_id=invoice.id,
            item_number=idx,
            description=item_data.description,
            hsn_sac_code=item_data.hsn_sac_code,
            quantity=item_data.quantity,
            unit=item_data.unit,
            unit_price=item_data.unit_price,
            discount_percent=item_data.discount_percent,
            **calc,
            gst_rate=item_data.gst_rate,
            cess_rate=item_data.cess_rate,
        )
        db.add(item)

        total_subtotal += calc["taxable_value"]
        total_cgst += calc["cgst_amount"]
        total_sgst += calc["sgst_amount"]
        total_igst += calc["igst_amount"]
        total_cess += calc["cess_amount"]
        total_discount += calc["discount_amount"]

    raw_total = total_subtotal + total_cgst + total_sgst + total_igst + total_cess
    round_off = round(round(raw_total) - raw_total, 2)
    grand_total = round(raw_total + round_off, 2)

    invoice.subtotal = round(total_subtotal, 2)
    invoice.total_cgst = round(total_cgst, 2)
    invoice.total_sgst = round(total_sgst, 2)
    invoice.total_igst = round(total_igst, 2)
    invoice.total_cess = round(total_cess, 2)
    invoice.total_discount = round(total_discount, 2)
    invoice.round_off = round_off
    invoice.grand_total = grand_total

    # ── Record on blockchain ──
    block_data = {
        "type": "invoice",
        "invoice_number": invoice_number,
        "vendor_id": vendor_id,
        "vendor_gstin": vendor.gstin,
        "buyer_name": data.buyer_name,
        "buyer_gstin": data.buyer_gstin or "B2C",
        "grand_total": grand_total,
        "invoice_date": data.invoice_date,
        "items_count": len(data.items),
    }
    block = add_block(db, "invoice", block_data)
    invoice.blockchain_hash = block.block_hash
    invoice.block_index = block.block_index

    db.commit()
    db.refresh(invoice)
    return invoice


@router.get("/vendor/{vendor_id}", response_model=List[InvoiceListResponse])
def list_vendor_invoices(vendor_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """List all invoices for a vendor."""
    invoices = db.query(Invoice).filter(Invoice.vendor_id == vendor_id).order_by(Invoice.id.desc()).all()
    return invoices


@router.get("/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(invoice_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get full invoice details with line items."""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.patch("/{invoice_id}/status")
def update_invoice_status(invoice_id: int, status: str, payment_status: str = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Update invoice or payment status."""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    valid_statuses = ["draft", "issued", "paid", "overdue", "cancelled"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of {valid_statuses}")

    invoice.invoice_status = status
    if payment_status:
        invoice.payment_status = payment_status
    db.commit()
    return {"message": "Status updated", "invoice_status": status}


@router.get("/{invoice_id}/pdf")
def download_invoice_pdf(invoice_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Download the invoice as a PDF file."""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    vendor = db.query(Vendor).filter(Vendor.id == invoice.vendor_id).first()
    items = db.query(InvoiceItem).filter(InvoiceItem.invoice_id == invoice_id).order_by(InvoiceItem.item_number).all()

    pdf_bytes = generate_invoice_pdf(invoice, vendor, items)

    filename = f"{invoice.invoice_number}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


class SendInvoiceEmailRequest(BaseModel):
    email: Optional[str] = None  # Override buyer_email if provided


@router.post("/{invoice_id}/send-email")
def send_invoice_email(invoice_id: int, data: SendInvoiceEmailRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Send the invoice PDF to the buyer via email."""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    recipient = data.email or invoice.buyer_email
    if not recipient:
        raise HTTPException(status_code=400, detail="No email address provided. Please specify an email.")

    vendor = db.query(Vendor).filter(Vendor.id == invoice.vendor_id).first()
    items = db.query(InvoiceItem).filter(InvoiceItem.invoice_id == invoice_id).order_by(InvoiceItem.item_number).all()

    pdf_bytes = generate_invoice_pdf(invoice, vendor, items)

    success = email_service.send_invoice_email(
        to=recipient,
        invoice_number=invoice.invoice_number,
        buyer_name=invoice.buyer_name,
        vendor_name=vendor.business_name if vendor else "InvoX Vendor",
        grand_total=invoice.grand_total,
        due_date=invoice.due_date,
        pdf_bytes=pdf_bytes,
    )

    if success:
        return {"message": f"Invoice sent to {recipient}", "email": recipient}
    else:
        raise HTTPException(status_code=500, detail="Failed to send email. Please try again.")
