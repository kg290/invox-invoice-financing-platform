# ══════════════════════════════════════════════════════════
# InvoX Telegram Bot + Backend — Single Launch Script
# ══════════════════════════════════════════════════════════
# Usage:  .\run_bot.ps1
# This starts:
#   1. FastAPI backend (port 8000)
#   2. Telegram bot (polling)
# Both share the same Python venv and TELEGRAM_BOT_TOKEN.
# Press Ctrl+C to stop both.
# ══════════════════════════════════════════════════════════

$ErrorActionPreference = "Stop"

# ── Config ──
$TELEGRAM_BOT_TOKEN = "8705153678:AAHGrFHCkPM1jFWuJlGQRugU1Leo8g2FOa4"
$BACKEND_PORT       = 8000
$BACKEND_URL        = "http://localhost:$BACKEND_PORT"

# ── Paths ──
$ROOT     = Split-Path -Parent $MyInvocation.MyCommand.Path
$BACKEND  = Join-Path $ROOT "backend"
$BOT_DIR  = Join-Path $ROOT "telegram-bot-package\bot"
$VENV_ACT = Join-Path $BACKEND "venv\Scripts\Activate.ps1"

# ── Activate venv ──
if (-Not (Test-Path $VENV_ACT)) {
    Write-Host "ERROR: Python venv not found at $VENV_ACT" -ForegroundColor Red
    Write-Host "Run:  cd backend; python -m venv venv; .\venv\Scripts\Activate.ps1; pip install -r requirements.txt"
    exit 1
}
& $VENV_ACT

# ── Export env vars (both backend and bot need them) ──
$env:TELEGRAM_BOT_TOKEN = $TELEGRAM_BOT_TOKEN
$env:BACKEND_URL        = $BACKEND_URL
$env:UPLOAD_DIR         = Join-Path $BACKEND "uploads"

Write-Host ""
Write-Host "═══════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  InvoX — Starting Backend + Telegram Bot  " -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# ── Start FastAPI backend as a background job ──
Write-Host "[1/2] Starting FastAPI backend on port $BACKEND_PORT..." -ForegroundColor Yellow
$backendJob = Start-Job -ScriptBlock {
    param($venvAct, $backendDir, $token, $uploadDir)
    & $venvAct
    $env:TELEGRAM_BOT_TOKEN = $token
    $env:UPLOAD_DIR = $uploadDir
    Set-Location $backendDir
    python -m uvicorn main:app --host 0.0.0.0 --port 8000
} -ArgumentList $VENV_ACT, $BACKEND, $TELEGRAM_BOT_TOKEN, $env:UPLOAD_DIR

# Wait for backend to be ready
Start-Sleep -Seconds 3
$retries = 0
while ($retries -lt 10) {
    try {
        $null = Invoke-WebRequest -Uri "$BACKEND_URL/openapi.json" -UseBasicParsing -TimeoutSec 2
        Write-Host "  Backend is UP at $BACKEND_URL" -ForegroundColor Green
        break
    } catch {
        $retries++
        Start-Sleep -Seconds 1
    }
}
if ($retries -ge 10) {
    Write-Host "  WARNING: Backend may not be ready yet." -ForegroundColor Red
}

# ── Start Telegram bot in foreground ──
Write-Host "[2/2] Starting Telegram Bot..." -ForegroundColor Yellow
Write-Host ""
Write-Host "  Bot token: $($TELEGRAM_BOT_TOKEN.Substring(0,10))..." -ForegroundColor DarkGray
Write-Host "  Backend:   $BACKEND_URL" -ForegroundColor DarkGray
Write-Host ""
Write-Host "Press Ctrl+C to stop both processes." -ForegroundColor DarkGray
Write-Host ""

try {
    Set-Location $BOT_DIR
    python invox_bot.py
} finally {
    # Cleanup: stop the backend job
    Write-Host ""
    Write-Host "Stopping backend..." -ForegroundColor Yellow
    Stop-Job -Job $backendJob -ErrorAction SilentlyContinue
    Remove-Job -Job $backendJob -Force -ErrorAction SilentlyContinue
    Write-Host "All processes stopped." -ForegroundColor Green
}
