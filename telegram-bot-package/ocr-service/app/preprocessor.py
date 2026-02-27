"""
preprocessor.py — Image preprocessing pipeline for invoice OCR.

Steps:
  1. Load image (from bytes, file path, or PDF page)
  2. Convert PDF pages to images via pdf2image
  3. Grayscale conversion
  4. Noise reduction (fastNlMeansDenoising)
  5. Deskew (correct rotation / skew)
  6. Adaptive binarisation (Otsu's threshold)
  7. Optional resize for better Tesseract accuracy

All functions accept and return numpy arrays (OpenCV format).
"""

import io
import math
import tempfile
from pathlib import Path
from typing import Union

import cv2
import numpy as np
from PIL import Image


def load_image_from_bytes(file_bytes: bytes) -> np.ndarray:
    """Convert raw file bytes into an OpenCV BGR image array."""
    arr = np.frombuffer(file_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image from provided bytes")
    return img


def pdf_to_images(pdf_bytes: bytes) -> list[np.ndarray]:
    """
    Convert a PDF file (as bytes) into a list of OpenCV images, one per page.
    Requires poppler installed on the system (poppler-utils on Linux,
    poppler on Windows via conda/chocolatey).
    """
    try:
        from pdf2image import convert_from_bytes
    except ImportError:
        raise ImportError("pdf2image is required for PDF processing. Install with: pip install pdf2image")

    try:
        pil_images = convert_from_bytes(pdf_bytes, dpi=300, fmt="png")
    except Exception as exc:
        print(f"  ⚠️  pdf2image failed: {exc}. Falling back to treating as single image.")
        return [load_image_from_bytes(pdf_bytes)]

    cv_images = []
    for pil_img in pil_images:
        # PIL → numpy → OpenCV BGR
        rgb = np.array(pil_img)
        bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        cv_images.append(bgr)
    return cv_images


def to_grayscale(img: np.ndarray) -> np.ndarray:
    """Convert BGR image to grayscale."""
    if len(img.shape) == 2:
        return img  # already grayscale
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def denoise(img: np.ndarray) -> np.ndarray:
    """Apply non-local means denoising to reduce noise while preserving edges."""
    return cv2.fastNlMeansDenoising(img, None, h=10, templateWindowSize=7, searchWindowSize=21)


def deskew(img: np.ndarray) -> np.ndarray:
    """
    Detect and correct skew angle using Hough line transform.
    Only corrects angles up to ±15° to avoid false corrections.
    """
    # Find edges
    edges = cv2.Canny(img, 50, 150, apertureSize=3)

    # Detect lines
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=100,
                            minLineLength=100, maxLineGap=10)
    if lines is None or len(lines) == 0:
        return img  # no lines detected — skip deskew

    # Calculate median angle
    angles = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        if x2 - x1 == 0:
            continue
        angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
        if abs(angle) < 15:  # only consider near-horizontal lines
            angles.append(angle)

    if not angles:
        return img

    median_angle = float(np.median(angles))

    if abs(median_angle) < 0.3:
        return img  # close enough to straight — skip

    # Rotate to correct skew
    h, w = img.shape[:2]
    center = (w // 2, h // 2)
    matrix = cv2.getRotationMatrix2D(center, median_angle, 1.0)
    rotated = cv2.warpAffine(img, matrix, (w, h),
                             flags=cv2.INTER_CUBIC,
                             borderMode=cv2.BORDER_REPLICATE)
    return rotated


def binarize(img: np.ndarray) -> np.ndarray:
    """Apply Otsu's adaptive binarisation for clean text extraction."""
    _, binary = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary


def resize_for_ocr(img: np.ndarray, target_dpi: int = 300) -> np.ndarray:
    """
    Upscale small images so Tesseract has enough detail.
    If image width is below 1500px, scale up to ~3000px wide.
    """
    h, w = img.shape[:2]
    if w < 1500:
        scale = 3000 / w
        new_w = int(w * scale)
        new_h = int(h * scale)
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
    return img


def preprocess(file_bytes: bytes, is_pdf: bool = False) -> list[np.ndarray]:
    """
    Full preprocessing pipeline. Returns a list of processed images
    (one per page for PDFs, single-element list for images).

    Pipeline: load → grayscale → resize → denoise → deskew → binarize
    """
    # Step 1: Load
    if is_pdf:
        raw_images = pdf_to_images(file_bytes)
    else:
        raw_images = [load_image_from_bytes(file_bytes)]

    processed = []
    for img in raw_images:
        # Step 2: Grayscale
        gray = to_grayscale(img)

        # Step 3: Resize if too small
        gray = resize_for_ocr(gray)

        # Step 4: Denoise
        clean = denoise(gray)

        # Step 5: Deskew
        straight = deskew(clean)

        # Step 6: Binarize
        binary = binarize(straight)

        processed.append(binary)

    return processed
