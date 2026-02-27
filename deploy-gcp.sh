#!/bin/bash
# ═══════════════════════════════════════════════════════════════
#  InvoX — Automated Google Cloud Run Deployment
# ═══════════════════════════════════════════════════════════════
#  Deploys both backend (FastAPI) and frontend (Next.js) to
#  Google Cloud Run using Artifact Registry.
#
#  Usage:  bash deploy-gcp.sh
# ═══════════════════════════════════════════════════════════════

set -e

# ── Configuration ──
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
REGION="asia-south1"
REPO_NAME="invox-repo"
BACKEND_SERVICE="invox-backend"
FRONTEND_SERVICE="invox-frontend"
REGISTRY="asia-south1-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}"
BACKEND_IMAGE="${REGISTRY}/${BACKEND_SERVICE}:latest"
FRONTEND_IMAGE="${REGISTRY}/${FRONTEND_SERVICE}:latest"

echo "═══════════════════════════════════════════════════"
echo "  InvoX — Google Cloud Run Deployment"
echo "  Project:  ${PROJECT_ID}"
echo "  Region:   ${REGION}"
echo "═══════════════════════════════════════════════════"
echo ""

# ── Step 1: Enable APIs ──
echo "[1/8] Enabling required Google Cloud APIs..."
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  --quiet 2>/dev/null

# ── Step 2: Create Artifact Registry (if not exists) ──
echo "[2/8] Ensuring Artifact Registry repository exists..."
gcloud artifacts repositories describe ${REPO_NAME} \
  --location=${REGION} --quiet 2>/dev/null || \
gcloud artifacts repositories create ${REPO_NAME} \
  --repository-format=docker \
  --location=${REGION} \
  --description="InvoX Docker images" \
  --quiet

# Configure Docker auth
gcloud auth configure-docker asia-south1-docker.pkg.dev --quiet 2>/dev/null

# ── Step 3: Build & Push Backend ──
echo ""
echo "[3/8] Building backend Docker image..."
docker build -t ${BACKEND_IMAGE} ./backend

echo "[3/8] Pushing backend image..."
docker push ${BACKEND_IMAGE}

# ── Step 4: Deploy Backend to Cloud Run ──
echo ""
echo "[4/8] Deploying backend to Cloud Run..."
gcloud run deploy ${BACKEND_SERVICE} \
  --image=${BACKEND_IMAGE} \
  --platform=managed \
  --region=${REGION} \
  --port=8000 \
  --memory=512Mi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=3 \
  --allow-unauthenticated \
  --set-env-vars="FRONTEND_URL=*,INVOX_PAY_SECRET=invox_pay_secret_k4x9m2p7q1w8e5,BLOCK_SIGNING_KEY=invox_chain_sign_k9x2m7p4q1w8e5r3,ENCRYPTION_KEY=invox_encrypt_a5b3c8d2e7f1g4h6,JWT_SECRET=invox-secret-key-change-in-production-2026" \
  --quiet

BACKEND_URL=$(gcloud run services describe ${BACKEND_SERVICE} --region=${REGION} --format="value(status.url)")
echo "Backend live at: ${BACKEND_URL}"

# ── Step 5: Build & Push Frontend (with backend URL baked in) ──
echo ""
echo "[5/8] Building frontend with API_URL=${BACKEND_URL}/api ..."
docker build \
  --build-arg NEXT_PUBLIC_API_URL="${BACKEND_URL}/api" \
  -t ${FRONTEND_IMAGE} \
  ./frontend

echo "[5/8] Pushing frontend image..."
docker push ${FRONTEND_IMAGE}

# ── Step 6: Deploy Frontend to Cloud Run ──
echo ""
echo "[6/8] Deploying frontend to Cloud Run..."
gcloud run deploy ${FRONTEND_SERVICE} \
  --image=${FRONTEND_IMAGE} \
  --platform=managed \
  --region=${REGION} \
  --port=3000 \
  --memory=256Mi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=3 \
  --allow-unauthenticated \
  --set-env-vars="NEXT_PUBLIC_API_URL=${BACKEND_URL}/api" \
  --quiet

FRONTEND_URL=$(gcloud run services describe ${FRONTEND_SERVICE} --region=${REGION} --format="value(status.url)")
echo "Frontend live at: ${FRONTEND_URL}"

# ── Step 7: Update Backend CORS with actual Frontend URL ──
echo ""
echo "[7/8] Updating backend CORS with frontend URL..."
gcloud run services update ${BACKEND_SERVICE} \
  --region=${REGION} \
  --update-env-vars="FRONTEND_URL=${FRONTEND_URL}" \
  --quiet

# ── Step 8: Seed Demo Data ──
echo ""
echo "[8/8] Seeding demo data..."
curl -s -X POST "${BACKEND_URL}/api/seed/" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('message','Seeded'))" 2>/dev/null || echo "(seed may already exist)"

echo ""
echo "========================================================"
echo "  DEPLOYMENT COMPLETE!"
echo ""
echo "  Frontend:  ${FRONTEND_URL}"
echo "  Backend:   ${BACKEND_URL}"
echo "  API Docs:  ${BACKEND_URL}/docs"
echo ""
echo "  Demo Logins (password: Demo@1234):"
echo "    vendor1@invox.demo  - Sunita (Tiffin Service)"
echo "    vendor2@invox.demo  - Ramu (Furniture Works)"
echo "    lender@invox.demo   - Deepak (Microfinance)"
echo "========================================================"
