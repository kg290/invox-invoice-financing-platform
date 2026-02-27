"""
Blockchain API Routes
═════════════════════
Exposes blockchain validation, exploration, and security endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import BlockchainBlock
from blockchain import validate_chain, get_block_details
from routes.auth import get_current_user

router = APIRouter(prefix="/api/blockchain", tags=["blockchain"])


@router.get("/validate")
def validate_blockchain(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Validate the entire blockchain — checks hashes, chain links, signatures, and PoW."""
    return validate_chain(db)


@router.get("/blocks")
def list_blocks(
    limit: int = 20,
    offset: int = 0,
    data_type: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List blockchain blocks with pagination and optional type filter."""
    q = db.query(BlockchainBlock).order_by(BlockchainBlock.block_index.desc())
    if data_type:
        q = q.filter(BlockchainBlock.data_type == data_type)
    total = q.count()
    blocks = q.offset(offset).limit(limit).all()
    return {
        "total": total,
        "blocks": [{
            "block_index": b.block_index,
            "data_type": b.data_type,
            "data_hash": b.data_hash,
            "block_hash": b.block_hash,
            "previous_hash": b.previous_hash,
            "nonce": b.nonce,
            "merkle_root": b.merkle_root,
            "is_encrypted": b.is_encrypted,
            "has_signature": bool(b.digital_signature),
            "timestamp": b.timestamp.isoformat() if b.timestamp else None,
        } for b in blocks],
    }


@router.get("/blocks/{block_index}")
def get_block(
    block_index: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get detailed information about a specific block including signature verification."""
    result = get_block_details(db, block_index)
    if not result:
        raise HTTPException(status_code=404, detail="Block not found")
    return result


@router.get("/stats")
def blockchain_stats(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get blockchain statistics and security summary."""
    total = db.query(BlockchainBlock).count()
    latest = db.query(BlockchainBlock).order_by(BlockchainBlock.block_index.desc()).first()

    type_counts = {}
    for row in db.query(BlockchainBlock.data_type).all():
        t = row[0]
        type_counts[t] = type_counts.get(t, 0) + 1

    signed = db.query(BlockchainBlock).filter(BlockchainBlock.digital_signature.isnot(None)).count()
    encrypted = db.query(BlockchainBlock).filter(BlockchainBlock.is_encrypted == True).count()

    return {
        "total_blocks": total,
        "latest_block_index": latest.block_index if latest else -1,
        "latest_block_hash": latest.block_hash if latest else None,
        "block_types": type_counts,
        "signed_blocks": signed,
        "encrypted_blocks": encrypted,
        "security_features": [
            "SHA-256 Hash Chaining",
            "HMAC-SHA256 Digital Signatures",
            "Merkle Tree Data Integrity",
            "Proof-of-Work (Difficulty 3)",
            "Duplicate Data Detection",
            "Data Encryption Support",
            "Chain Tamper Detection",
        ],
    }
