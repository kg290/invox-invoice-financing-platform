"""
subscriber.py — Redis subscriber that listens for OCR_REQUESTED events.

When the invoice-service publishes an OCR_REQUESTED event (containing
an invoice_id and file_path), this subscriber:
  1. Reads the file from disk
  2. Runs the preprocessing + OCR + extraction pipeline
  3. Calls back to the invoice-service with the extracted data
  4. Publishes VERIFY_REQUESTED for the verification service
"""

import asyncio
import json
import os
import threading
from pathlib import Path

from app.events import subscribe, publish, OCR_REQUESTED, OCR_COMPLETED, VERIFY_REQUESTED
from app.preprocessor import preprocess
from app.extractor import ocr_images, extract_invoice_data
from app.invoice_client import patch_invoice_ocr


def _is_pdf(filename: str) -> bool:
    return filename.lower().endswith(".pdf")


async def _process_ocr_event(payload: dict) -> None:
    """Process a single OCR_REQUESTED event."""
    invoice_id = payload.get("invoice_id")
    file_path = payload.get("file_path")
    auth_token = payload.get("auth_token")

    if not invoice_id or not file_path:
        print(f"  ❌ Invalid OCR_REQUESTED payload: {payload}")
        return

    print(f"\n{'='*50}")
    print(f"  📄 OCR_REQUESTED: invoice_id={invoice_id}")
    print(f"  📁 File: {file_path}")
    print(f"{'='*50}")

    # Read the file
    file_path_obj = Path(file_path)
    if not file_path_obj.exists():
        print(f"  ❌ File not found: {file_path}")
        return

    file_bytes = file_path_obj.read_bytes()
    is_pdf = _is_pdf(file_path)

    # Run pipeline
    try:
        print("  🖼️  Preprocessing...")
        images = preprocess(file_bytes, is_pdf=is_pdf)

        print(f"  🔍 Running OCR on {len(images)} page(s)...")
        raw_text = ocr_images(images)

        print("  📊 Extracting fields...")
        extracted = extract_invoice_data(raw_text)
        extracted["raw_text"] = raw_text[:2000]  # truncate for storage

        print(f"  ✅ Extraction complete — confidence: {extracted['confidence_score']}")
        if extracted["warnings"]:
            for w in extracted["warnings"]:
                print(f"     ⚠️  {w}")

        # Callback to invoice service
        await patch_invoice_ocr(invoice_id, extracted, auth_token)

        # Publish completion events
        event_payload = {
            "invoice_id": invoice_id,
            "confidence_score": extracted["confidence_score"],
            "status": "ocr_done",
        }
        publish(OCR_COMPLETED, event_payload)
        publish(VERIFY_REQUESTED, event_payload)

    except Exception as exc:
        print(f"  ❌ OCR pipeline failed for invoice #{invoice_id}: {exc}")
        import traceback
        traceback.print_exc()


def start_subscriber() -> None:
    """
    Start the Redis subscriber in a background thread.
    Listens on the OCR_REQUESTED channel indefinitely.
    """
    def _listen():
        try:
            ps = subscribe(OCR_REQUESTED)
            print(f"  📡 Subscribed to Redis channel: {OCR_REQUESTED}")
            print(f"  ⏳ Waiting for OCR_REQUESTED events...")

            for message in ps.listen():
                if message["type"] != "message":
                    continue

                try:
                    payload = json.loads(message["data"])
                    # Run the async handler
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(_process_ocr_event(payload))
                    loop.close()
                except json.JSONDecodeError:
                    print(f"  ❌ Invalid JSON in OCR_REQUESTED: {message['data']}")
                except Exception as exc:
                    print(f"  ❌ Error handling OCR_REQUESTED: {exc}")

        except Exception as exc:
            print(f"  ⚠️  Redis subscriber failed: {exc}")
            print(f"  ℹ️  OCR service will still work via direct HTTP upload.")

    thread = threading.Thread(target=_listen, daemon=True, name="ocr-subscriber")
    thread.start()
    print("  🚀 Redis subscriber thread started")
