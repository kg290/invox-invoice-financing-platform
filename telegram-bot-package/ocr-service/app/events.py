"""
events.py — Redis pub/sub helpers for the InvoX OCR pipeline.

Channels:
  OCR_REQUESTED   — published by invoice-service when an invoice file is uploaded
  OCR_COMPLETED   — published by this service after extraction is done
  VERIFY_REQUESTED — published by this service so verification-service picks up next
"""

import json
import os
import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Channel names
OCR_REQUESTED = "OCR_REQUESTED"
OCR_COMPLETED = "OCR_COMPLETED"
VERIFY_REQUESTED = "VERIFY_REQUESTED"


def get_redis() -> redis.Redis:
    """Return a Redis client. Connection is lazy — no crash if Redis is down."""
    return redis.from_url(REDIS_URL, decode_responses=True)


def publish(channel: str, payload: dict) -> bool:
    """
    Publish a JSON payload to a Redis channel.
    Returns True on success, False if Redis is unreachable.
    """
    try:
        r = get_redis()
        r.publish(channel, json.dumps(payload))
        print(f"  📡 Published to {channel}: invoice_id={payload.get('invoice_id')}")
        return True
    except redis.ConnectionError:
        print(f"  ⚠️  Redis unavailable — skipped publish to {channel}")
        return False
    except Exception as exc:
        print(f"  ❌ Redis publish error: {exc}")
        return False


def subscribe(channel: str):
    """
    Return a Redis pubsub subscription for the given channel.
    Caller should iterate over subscription.listen() in a loop.
    """
    r = get_redis()
    ps = r.pubsub()
    ps.subscribe(channel)
    return ps
