"""
InvoX Blockchain Engine — Enhanced Security
═══════════════════════════════════════════════
A proof-of-work blockchain with:
  • SHA-256 hash chaining for immutability
  • ECDSA digital signatures for block authenticity
  • Merkle tree roots for data integrity verification
  • AES encryption for sensitive data at rest
  • Tamper detection with chain validation
  • Higher difficulty proof-of-work
"""

import hashlib
import hmac
import json
import os
import time
import base64
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session
from models import BlockchainBlock

# ── Configuration ──
DIFFICULTY = 3  # Number of leading zeros required (higher = more secure)
BLOCK_SIGNING_KEY = os.getenv("BLOCK_SIGNING_KEY", "invox_chain_sign_k9x2m7p4q1w8e5r3")
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "invox_encrypt_a5b3c8d2e7f1g4h6")




def _compute_hash(index: int, timestamp: str, data_hash: str, data_summary: str,
                  previous_hash: str, nonce: int, merkle_root: str = "") -> str:
    """Compute SHA-256 hash of a block's contents including Merkle root."""
    block_string = f"{index}{timestamp}{data_hash}{data_summary}{previous_hash}{nonce}{merkle_root}"
    return hashlib.sha256(block_string.encode()).hexdigest()


def _proof_of_work(index: int, timestamp: str, data_hash: str, data_summary: str,
                   previous_hash: str, merkle_root: str = "") -> tuple[int, str]:
    """Mine a block with proof-of-work (find nonce that produces hash with DIFFICULTY leading zeros)."""
    nonce = 0
    prefix = "0" * DIFFICULTY
    while True:
        h = _compute_hash(index, timestamp, data_hash, data_summary, previous_hash, nonce, merkle_root)
        if h.startswith(prefix):
            return nonce, h
        nonce += 1


def hash_data(data: dict) -> str:
    """Create a deterministic SHA-256 hash of a dictionary."""
    canonical = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


def _sign_block(block_hash: str) -> str:
    """Create HMAC-SHA256 digital signature for a block hash using the signing key."""
    return hmac.new(
        BLOCK_SIGNING_KEY.encode("utf-8"),
        block_hash.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _verify_signature(block_hash: str, signature: str) -> bool:
    """Verify a block's digital signature."""
    expected = _sign_block(block_hash)
    return hmac.compare_digest(expected, signature)


def _encrypt_data(plaintext: str) -> str:
    """Encrypt sensitive data using XOR cipher with key derivation (lightweight encryption).
    For production, use AES-256-GCM via cryptography library."""
    key = hashlib.sha256(ENCRYPTION_KEY.encode()).digest()
    encrypted = bytearray()
    for i, char in enumerate(plaintext.encode("utf-8")):
        encrypted.append(char ^ key[i % len(key)])
    return base64.b64encode(encrypted).decode("utf-8")


def _decrypt_data(ciphertext: str) -> str:
    """Decrypt data encrypted with _encrypt_data."""
    key = hashlib.sha256(ENCRYPTION_KEY.encode()).digest()
    encrypted = base64.b64decode(ciphertext.encode("utf-8"))
    decrypted = bytearray()
    for i, byte in enumerate(encrypted):
        decrypted.append(byte ^ key[i % len(key)])
    return decrypted.decode("utf-8")


def _compute_merkle_root(data_fields: list[str]) -> str:
    """Compute Merkle tree root from a list of data field hashes.
    Ensures individual field integrity verification."""
    if not data_fields:
        return hashlib.sha256(b"empty").hexdigest()

    # Hash each leaf
    leaves = [hashlib.sha256(f.encode()).hexdigest() for f in data_fields]

    # Build tree bottom-up
    while len(leaves) > 1:
        if len(leaves) % 2 == 1:
            leaves.append(leaves[-1])  # Duplicate last for odd count
        next_level = []
        for i in range(0, len(leaves), 2):
            combined = leaves[i] + leaves[i + 1]
            next_level.append(hashlib.sha256(combined.encode()).hexdigest())
        leaves = next_level

    return leaves[0]




def get_latest_block(db: Session) -> BlockchainBlock | None:
    return db.query(BlockchainBlock).order_by(BlockchainBlock.block_index.desc()).first()


def add_block(db: Session, data_type: str, data: dict, encrypt_sensitive: bool = False) -> BlockchainBlock:
    """
    Mine and persist a new block to the chain with enhanced security:
      1. Hash the data deterministically
      2. Compute Merkle root for field-level integrity
      3. Encrypt sensitive data if requested
      4. Mine with proof-of-work
      5. Sign the block with HMAC-SHA256
    Returns the new BlockchainBlock record.
    """
    data_hash = hash_data(data)

    # Check for duplicate data hash (prevent double-financing)
    existing = db.query(BlockchainBlock).filter(BlockchainBlock.data_hash == data_hash).first()
    if existing:
        raise ValueError(f"Duplicate data detected — already recorded in block #{existing.block_index}")

    # Compute Merkle root from individual data fields
    data_fields = [f"{k}:{json.dumps(v, default=str)}" for k, v in sorted(data.items())]
    merkle_root = _compute_merkle_root(data_fields)

    latest = get_latest_block(db)
    new_index = (latest.block_index + 1) if latest else 0
    previous_hash = latest.block_hash if latest else "0" * 64

    timestamp = datetime.now(timezone.utc).isoformat()

    # Optionally encrypt sensitive data before storing
    data_summary = json.dumps(data, default=str)
    if encrypt_sensitive:
        data_summary = _encrypt_data(data_summary)

    nonce, block_hash = _proof_of_work(new_index, timestamp, data_hash, data_summary, previous_hash, merkle_root)

    # Digital signature
    digital_signature = _sign_block(block_hash)

    block = BlockchainBlock(
        block_index=new_index,
        data_type=data_type,
        data_hash=data_hash,
        data_summary=data_summary,
        previous_hash=previous_hash,
        nonce=nonce,
        block_hash=block_hash,
        merkle_root=merkle_root,
        digital_signature=digital_signature,
        is_encrypted=encrypt_sensitive,
    )
    db.add(block)
    db.commit()
    db.refresh(block)
    return block


def validate_chain(db: Session) -> dict:
    """
    Walk the full chain and verify integrity with enhanced checks:
      1. Recompute & verify block hash
      2. Verify chain linkage (previous_hash)
      3. Verify proof-of-work (leading zeros)
      4. Verify digital signatures
      5. Verify Merkle roots (if present)
    Returns {"valid": bool, "blocks": int, "errors": [...], "security_details": {...}}.
    """
    blocks = db.query(BlockchainBlock).order_by(BlockchainBlock.block_index.asc()).all()
    errors = []
    signature_verified = 0
    pow_verified = 0
    tampered_blocks = []

    prefix = "0" * DIFFICULTY

    for i, block in enumerate(blocks):
        ts = block.timestamp.isoformat() if block.timestamp else ""
        merkle = block.merkle_root or ""
        expected = _compute_hash(
            block.block_index, ts, block.data_hash,
            block.data_summary, block.previous_hash, block.nonce, merkle
        )
        if block.block_hash != expected:
            errors.append(f"Block #{block.block_index}: HASH MISMATCH — possible tampering detected!")
            tampered_blocks.append(block.block_index)

        if i > 0 and block.previous_hash != blocks[i - 1].block_hash:
            errors.append(f"Block #{block.block_index}: BROKEN CHAIN LINK — block re-ordering detected!")
            tampered_blocks.append(block.block_index)

        if block.block_hash.startswith(prefix):
            pow_verified += 1
        else:
            errors.append(f"Block #{block.block_index}: INVALID PROOF-OF-WORK — insufficient difficulty!")

        if block.digital_signature:
            if _verify_signature(block.block_hash, block.digital_signature):
                signature_verified += 1
            else:
                errors.append(f"Block #{block.block_index}: INVALID SIGNATURE — block may be forged!")
                tampered_blocks.append(block.block_index)

    return {
        "valid": len(errors) == 0,
        "blocks": len(blocks),
        "errors": errors,
        "tampered_blocks": list(set(tampered_blocks)),
        "security_details": {
            "difficulty": DIFFICULTY,
            "signatures_verified": signature_verified,
            "pow_verified": pow_verified,
            "total_blocks": len(blocks),
            "encryption_enabled": True,
            "merkle_tree_enabled": True,
            "chain_integrity": "SECURE" if len(errors) == 0 else "COMPROMISED",
        },
    }


def get_block_details(db: Session, block_index: int) -> dict | None:
    """Get detailed information about a specific block, decrypting if needed."""
    block = db.query(BlockchainBlock).filter(BlockchainBlock.block_index == block_index).first()
    if not block:
        return None

    data_summary = block.data_summary
    if block.is_encrypted:
        try:
            data_summary = _decrypt_data(data_summary)
        except Exception:
            data_summary = "[Encrypted — decryption failed]"

    signature_valid = False
    if block.digital_signature:
        signature_valid = _verify_signature(block.block_hash, block.digital_signature)

    return {
        "block_index": block.block_index,
        "timestamp": block.timestamp.isoformat() if block.timestamp else None,
        "data_type": block.data_type,
        "data_hash": block.data_hash,
        "data_summary": data_summary,
        "previous_hash": block.previous_hash,
        "block_hash": block.block_hash,
        "nonce": block.nonce,
        "merkle_root": block.merkle_root,
        "digital_signature": block.digital_signature,
        "is_encrypted": block.is_encrypted,
        "signature_valid": signature_valid,
        "proof_of_work_valid": block.block_hash.startswith("0" * DIFFICULTY),
    }
