"""
Blockchain Invoice Registry Routes
═══════════════════════════════════
Immutable proof of every invoice — tamper-proof, legally binding.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from database import get_db
from models import Invoice, InvoiceRegistryEntry
from routes.auth import get_current_user
from services.blockchain_registry import (
    register_invoice_on_blockchain,
    verify_invoice_integrity,
    get_invoice_audit_trail,
)

router = APIRouter(prefix="/api/blockchain-registry", tags=["Blockchain Invoice Registry"])


@router.post("/register/{invoice_id}")
def register_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Register an invoice on the blockchain.
    Creates immutable hash, vendor signature, Merkle root, and blockchain block.
    Detects duplicate invoices automatically.
    """
    try:
        result = register_invoice_on_blockchain(db, invoice_id)
        return {
            "message": "Invoice registered on blockchain successfully",
            **result,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/verify/{invoice_id}")
def verify_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Verify invoice integrity against blockchain.
    Re-computes hash and compares with registered hash.
    Detects any tampering with invoice data.
    """
    result = verify_invoice_integrity(db, invoice_id)
    if not result.get("verified") and result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/certificate/{invoice_id}")
def get_registry_certificate(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get a tamper-proof certificate for an invoice.
    Contains all cryptographic proofs needed for legal/audit purposes.
    """
    entry = db.query(InvoiceRegistryEntry).filter(
        InvoiceRegistryEntry.invoice_id == invoice_id
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Invoice not registered on blockchain")

    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()

    # Re-verify before issuing certificate
    verification = verify_invoice_integrity(db, invoice_id)

    return {
        "certificate_type": "InvoX Blockchain Registry Certificate",
        "issued_at": datetime.now(timezone.utc).isoformat(),
        "invoice": {
            "id": invoice_id,
            "number": invoice.invoice_number if invoice else None,
            "date": invoice.invoice_date if invoice else None,
            "grand_total": invoice.grand_total if invoice else None,
            "buyer_name": invoice.buyer_name if invoice else None,
        },
        "cryptographic_proof": {
            "invoice_hash": entry.invoice_hash,
            "vendor_signature": entry.vendor_signature,
            "buyer_gstin_hash": entry.buyer_gstin_hash,
            "merkle_root": entry.merkle_root,
            "algorithm": "SHA-256 + HMAC-SHA256",
        },
        "blockchain_anchor": {
            "block_index": entry.block_index,
            "block_hash": entry.block_hash,
            "chain": "InvoX Private Blockchain (PoW, Difficulty=3)",
        },
        "integrity_verification": verification,
        "legal_notice": (
            "This certificate provides cryptographic proof that the invoice was registered "
            "on InvoX blockchain at the time indicated. Any modification to the invoice data "
            "after registration will be detected through hash comparison. "
            "Blockchain evidence is admissible in Indian courts under the IT Act, 2000 (Section 65B)."
        ),
    }


@router.get("/history/{invoice_id}")
def get_invoice_history(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get complete audit trail of an invoice from blockchain.
    Shows every event: creation, listing, funding, repayment, settlement.
    """
    result = get_invoice_audit_trail(db, invoice_id)
    if not result.get("registry"):
        raise HTTPException(status_code=404, detail="Invoice not found in registry")
    return result


@router.get("/stats")
def registry_stats(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get overall blockchain registry statistics."""
    total = db.query(InvoiceRegistryEntry).count()
    registered = db.query(InvoiceRegistryEntry).filter(
        InvoiceRegistryEntry.registration_status == "registered"
    ).count()
    tampered = db.query(InvoiceRegistryEntry).filter(
        InvoiceRegistryEntry.registration_status == "tampered"
    ).count()
    total_checks = db.query(InvoiceRegistryEntry).with_entities(
        InvoiceRegistryEntry.tamper_check_count
    ).all()
    total_verifications = sum(c[0] for c in total_checks)

    return {
        "total_registered": total,
        "status_breakdown": {
            "registered": registered,
            "tampered": tampered,
            "pending": total - registered - tampered,
        },
        "total_integrity_checks": total_verifications,
        "registry_health": "SECURE" if tampered == 0 else f"ALERT: {tampered} tampered invoice(s)",
    }
