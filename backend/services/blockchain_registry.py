"""
Blockchain Invoice Registry — Immutable Invoice Truth Layer
═══════════════════════════════════════════════════════════════
Registers every invoice on the blockchain with:
  • Deterministic SHA-256 hash of canonical invoice data
  • Vendor HMAC-SHA256 signature (proves vendor authorized this)
  • Buyer GSTIN hash (links to buyer without exposing raw GSTIN)
  • Merkle root across all invoice fields (field-level integrity)
  • Duplicate detection (same invoice content = REJECTED)
  • Tamper verification (re-hash and compare at any time)
"""

import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from models import Invoice, InvoiceItem, Vendor, InvoiceRegistryEntry, BlockchainBlock
from blockchain import add_block, hash_data, _compute_merkle_root, _sign_block

# Signing key for vendor invoice signatures
INVOICE_SIGNING_KEY = "invox_invoice_registry_k7m2p5q9w1e4r8"


def _canonical_invoice_data(invoice: Invoice, items: list[InvoiceItem], vendor: Vendor) -> dict:
    """
    Build a deterministic, canonical representation of the invoice.
    This is the data that gets hashed — any change breaks the hash.
    """
    canonical_items = []
    for item in sorted(items, key=lambda x: x.item_number):
        canonical_items.append({
            "item_number": item.item_number,
            "description": item.description,
            "hsn_sac_code": item.hsn_sac_code,
            "quantity": item.quantity,
            "unit": item.unit,
            "unit_price": item.unit_price,
            "gst_rate": item.gst_rate,
            "taxable_value": item.taxable_value,
            "total_amount": item.total_amount,
        })

    return {
        "invoice_number": invoice.invoice_number,
        "invoice_date": invoice.invoice_date,
        "due_date": invoice.due_date,
        "vendor_gstin": vendor.gstin,
        "vendor_pan": vendor.personal_pan,
        "buyer_name": invoice.buyer_name,
        "buyer_gstin": invoice.buyer_gstin or "B2C",
        "supply_type": invoice.supply_type,
        "place_of_supply": invoice.place_of_supply,
        "subtotal": invoice.subtotal,
        "total_cgst": invoice.total_cgst,
        "total_sgst": invoice.total_sgst,
        "total_igst": invoice.total_igst,
        "grand_total": invoice.grand_total,
        "items": canonical_items,
    }


def _compute_invoice_hash(canonical_data: dict) -> str:
    """SHA-256 of the canonical invoice JSON."""
    raw = json.dumps(canonical_data, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _sign_invoice(invoice_hash: str, vendor_gstin: str) -> str:
    """HMAC-SHA256 signature binding invoice hash to vendor identity."""
    message = f"{invoice_hash}|{vendor_gstin}"
    return hmac.new(
        INVOICE_SIGNING_KEY.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _hash_buyer_gstin(buyer_gstin: str) -> str:
    """Hash buyer GSTIN for privacy-preserving linking."""
    return hashlib.sha256(buyer_gstin.encode("utf-8")).hexdigest()


def register_invoice_on_blockchain(db: Session, invoice_id: int) -> dict:
    """
    Register an invoice on the blockchain registry.
    Returns registry entry details or raises ValueError on failure.
    """
    # Fetch invoice, items, vendor
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise ValueError("Invoice not found")

    vendor = db.query(Vendor).filter(Vendor.id == invoice.vendor_id).first()
    if not vendor:
        raise ValueError("Vendor not found")

    items = db.query(InvoiceItem).filter(
        InvoiceItem.invoice_id == invoice_id
    ).order_by(InvoiceItem.item_number).all()

    # Check if already registered
    existing = db.query(InvoiceRegistryEntry).filter(
        InvoiceRegistryEntry.invoice_id == invoice_id
    ).first()
    if existing:
        raise ValueError(f"Invoice already registered on blockchain (registry #{existing.id})")

    # Build canonical data and compute hash
    canonical = _canonical_invoice_data(invoice, items, vendor)
    invoice_hash = _compute_invoice_hash(canonical)

    # Check for duplicate content hash (same data from different invoice IDs = fraud)
    duplicate = db.query(InvoiceRegistryEntry).filter(
        InvoiceRegistryEntry.invoice_hash == invoice_hash
    ).first()
    if duplicate:
        raise ValueError(
            f"DUPLICATE DETECTED: Invoice content matches existing registry entry #{duplicate.id} "
            f"(invoice_id={duplicate.invoice_id}). Possible duplicate/fraudulent invoice."
        )

    # Generate vendor signature
    vendor_signature = _sign_invoice(invoice_hash, vendor.gstin)

    # Hash buyer GSTIN for privacy
    buyer_gstin_hash = _hash_buyer_gstin(invoice.buyer_gstin) if invoice.buyer_gstin else None

    # Compute Merkle root across all fields for field-level integrity
    field_values = [f"{k}:{json.dumps(v, default=str)}" for k, v in sorted(canonical.items())]
    merkle_root = _compute_merkle_root(field_values)

    # Record on blockchain
    block_data = {
        "type": "invoice_registry",
        "invoice_id": invoice_id,
        "invoice_number": invoice.invoice_number,
        "invoice_hash": invoice_hash,
        "vendor_gstin": vendor.gstin,
        "buyer_gstin_hash": buyer_gstin_hash,
        "vendor_signature": vendor_signature,
        "merkle_root": merkle_root,
        "grand_total": invoice.grand_total,
        "registered_at": datetime.now(timezone.utc).isoformat(),
    }
    block = add_block(db, "invoice_registry", block_data, encrypt_sensitive=True)

    # Create registry entry
    entry = InvoiceRegistryEntry(
        invoice_id=invoice_id,
        vendor_id=vendor.id,
        invoice_hash=invoice_hash,
        vendor_signature=vendor_signature,
        buyer_gstin_hash=buyer_gstin_hash,
        block_index=block.block_index,
        block_hash=block.block_hash,
        merkle_root=merkle_root,
        registration_status="registered",
        last_verified_at=datetime.now(timezone.utc),
        verification_result="intact",
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    return {
        "registry_id": entry.id,
        "invoice_id": invoice_id,
        "invoice_hash": invoice_hash,
        "vendor_signature": vendor_signature,
        "buyer_gstin_hash": buyer_gstin_hash,
        "merkle_root": merkle_root,
        "block_index": block.block_index,
        "block_hash": block.block_hash,
        "registration_status": "registered",
    }


def verify_invoice_integrity(db: Session, invoice_id: int) -> dict:
    """
    Re-compute the invoice hash and compare with the registered hash.
    Detects any tampering with invoice data after registration.
    """
    entry = db.query(InvoiceRegistryEntry).filter(
        InvoiceRegistryEntry.invoice_id == invoice_id
    ).first()
    if not entry:
        return {"verified": False, "error": "Invoice not registered on blockchain"}

    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    vendor = db.query(Vendor).filter(Vendor.id == invoice.vendor_id).first()
    items = db.query(InvoiceItem).filter(
        InvoiceItem.invoice_id == invoice_id
    ).order_by(InvoiceItem.item_number).all()

    # Recompute hash
    canonical = _canonical_invoice_data(invoice, items, vendor)
    current_hash = _compute_invoice_hash(canonical)

    # Compare
    hash_match = current_hash == entry.invoice_hash
    sig_valid = _sign_invoice(entry.invoice_hash, vendor.gstin) == entry.vendor_signature

    # Verify blockchain block exists
    block_valid = False
    if entry.block_hash:
        block = db.query(BlockchainBlock).filter(
            BlockchainBlock.block_hash == entry.block_hash
        ).first()
        block_valid = block is not None

    # Update verification record
    entry.tamper_check_count += 1
    entry.last_verified_at = datetime.now(timezone.utc)
    result = "intact" if (hash_match and sig_valid and block_valid) else "tampered"
    entry.verification_result = result
    if result == "tampered":
        entry.registration_status = "tampered"
    db.commit()

    return {
        "verified": result == "intact",
        "invoice_id": invoice_id,
        "registered_hash": entry.invoice_hash,
        "current_hash": current_hash,
        "hash_match": hash_match,
        "signature_valid": sig_valid,
        "blockchain_anchored": block_valid,
        "block_hash": entry.block_hash,
        "tamper_check_count": entry.tamper_check_count,
        "result": result,
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }


def get_invoice_audit_trail(db: Session, invoice_id: int) -> dict:
    """Get complete audit trail of an invoice from blockchain."""
    entry = db.query(InvoiceRegistryEntry).filter(
        InvoiceRegistryEntry.invoice_id == invoice_id
    ).first()

    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()

    # Find all blockchain blocks related to this invoice
    blocks = db.query(BlockchainBlock).filter(
        BlockchainBlock.data_summary.contains(f'"invoice_id": {invoice_id}') |
        BlockchainBlock.data_summary.contains(f'"invoice_number": "{invoice.invoice_number}"')
    ).order_by(BlockchainBlock.block_index.asc()).all() if invoice else []

    trail = []
    for b in blocks:
        trail.append({
            "block_index": b.block_index,
            "data_type": b.data_type,
            "block_hash": b.block_hash,
            "timestamp": b.timestamp.isoformat() if b.timestamp else None,
            "is_encrypted": b.is_encrypted,
        })

    return {
        "invoice_id": invoice_id,
        "invoice_number": invoice.invoice_number if invoice else None,
        "registry": {
            "id": entry.id if entry else None,
            "invoice_hash": entry.invoice_hash if entry else None,
            "block_hash": entry.block_hash if entry else None,
            "registration_status": entry.registration_status if entry else "not_registered",
            "verification_result": entry.verification_result if entry else None,
            "registered_at": entry.created_at.isoformat() if entry and entry.created_at else None,
        } if entry else None,
        "blockchain_trail": trail,
        "total_events": len(trail),
    }
