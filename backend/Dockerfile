# ═══════════════════════════════════════════════
#  InvoX Backend — Dockerfile
# ═══════════════════════════════════════════════
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create uploads directory
RUN mkdir -p uploads

# Expose port (Cloud Run uses $PORT)
EXPOSE 8000

# Health check (local/compose only; Cloud Run ignores this)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run with uvicorn — Cloud Run sets $PORT
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
