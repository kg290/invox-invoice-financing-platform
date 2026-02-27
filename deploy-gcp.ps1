# ═══════════════════════════════════════════════
#  InvoX — Google Cloud Deployment Script (Windows)
# ═══════════════════════════════════════════════
#  Account: karnajeetgosavi2908@gmail.com
#  Run: .\deploy-gcp.ps1
# ═══════════════════════════════════════════════

$ErrorActionPreference = "Stop"
$PROJECT_ID = "invox-platform"
$REGION = "asia-south1"
$REPO = "invox-repo"

Write-Host "`n═══ InvoX GCP Deployment ═══`n" -ForegroundColor Cyan

# ── Step 1: Check gcloud CLI ──
Write-Host "[1/8] Checking Google Cloud CLI..." -ForegroundColor Yellow
try {
    gcloud --version | Select-Object -First 1
} catch {
    Write-Host "ERROR: gcloud CLI not installed. Download from https://cloud.google.com/sdk/docs/install" -ForegroundColor Red
    exit 1
}

# ── Step 2: Login & Set Project ──
Write-Host "`n[2/8] Logging in to Google Cloud..." -ForegroundColor Yellow
gcloud auth login --account=karnajeetgosavi2908@gmail.com

# Create project if not exists
$projects = gcloud projects list --format="value(projectId)" 2>$null
if ($projects -notcontains $PROJECT_ID) {
    Write-Host "Creating project $PROJECT_ID..." -ForegroundColor Yellow
    gcloud projects create $PROJECT_ID --name="InvoX Platform"
}
gcloud config set project $PROJECT_ID

# ── Step 3: Enable APIs ──
Write-Host "`n[3/8] Enabling required APIs..." -ForegroundColor Yellow
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable artifactregistry.googleapis.com

# ── Step 4: Create Artifact Registry ──
Write-Host "`n[4/8] Setting up Artifact Registry..." -ForegroundColor Yellow
$repos = gcloud artifacts repositories list --location=$REGION --format="value(name)" 2>$null
if ($repos -notcontains $REPO) {
    gcloud artifacts repositories create $REPO `
        --repository-format=docker `
        --location=$REGION `
        --description="InvoX Docker images"
}
gcloud auth configure-docker "$REGION-docker.pkg.dev" --quiet

# ── Step 5: Build & Deploy Backend ──
Write-Host "`n[5/8] Building & deploying backend..." -ForegroundColor Yellow
$BACKEND_IMAGE = "$REGION-docker.pkg.dev/$PROJECT_ID/$REPO/invox-backend:latest"

Push-Location backend
docker build -t $BACKEND_IMAGE .
docker push $BACKEND_IMAGE

gcloud run deploy invox-backend `
    --image=$BACKEND_IMAGE `
    --platform=managed `
    --region=$REGION `
    --port=8000 `
    --memory=512Mi `
    --cpu=1 `
    --min-instances=0 `
    --max-instances=3 `
    --allow-unauthenticated `
    --set-env-vars="INVOX_PAY_SECRET=invox_pay_secret_k4x9m2p7q1w8e5,BLOCK_SIGNING_KEY=invox_chain_sign_k9x2m7p4q1w8e5r3,ENCRYPTION_KEY=invox_encrypt_a5b3c8d2e7f1g4h6"
Pop-Location

# Get backend URL
$BACKEND_URL = gcloud run services describe invox-backend --region=$REGION --format="value(status.url)"
Write-Host "Backend URL: $BACKEND_URL" -ForegroundColor Green

# ── Step 6: Build & Deploy Frontend ──
Write-Host "`n[6/8] Building & deploying frontend..." -ForegroundColor Yellow
$FRONTEND_IMAGE = "$REGION-docker.pkg.dev/$PROJECT_ID/$REPO/invox-frontend:latest"
$API_URL = "$BACKEND_URL/api"

Push-Location frontend
docker build --build-arg NEXT_PUBLIC_API_URL=$API_URL -t $FRONTEND_IMAGE .
docker push $FRONTEND_IMAGE

gcloud run deploy invox-frontend `
    --image=$FRONTEND_IMAGE `
    --platform=managed `
    --region=$REGION `
    --port=3000 `
    --memory=512Mi `
    --cpu=1 `
    --min-instances=0 `
    --max-instances=3 `
    --allow-unauthenticated `
    --set-env-vars="NEXT_PUBLIC_API_URL=$API_URL"
Pop-Location

# Get frontend URL
$FRONTEND_URL = gcloud run services describe invox-frontend --region=$REGION --format="value(status.url)"
Write-Host "Frontend URL: $FRONTEND_URL" -ForegroundColor Green

# ── Step 7: Update Backend CORS ──
Write-Host "`n[7/8] Updating backend CORS..." -ForegroundColor Yellow
gcloud run services update invox-backend `
    --region=$REGION `
    --update-env-vars="FRONTEND_URL=$FRONTEND_URL"

# ── Step 8: Seed Database ──
Write-Host "`n[8/8] Seeding demo data..." -ForegroundColor Yellow
try {
    Invoke-RestMethod -Method POST -Uri "$BACKEND_URL/api/seed/demo" | Out-Null
    Write-Host "Demo data seeded!" -ForegroundColor Green
} catch {
    Write-Host "Seed failed (may need to retry): $_" -ForegroundColor Yellow
}

# ── Done! ──
Write-Host "`n═══════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  InvoX Deployment Complete!" -ForegroundColor Green
Write-Host "  Backend:  $BACKEND_URL" -ForegroundColor White
Write-Host "  Frontend: $FRONTEND_URL" -ForegroundColor White
Write-Host "═══════════════════════════════════════`n" -ForegroundColor Cyan
