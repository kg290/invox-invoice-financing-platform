# InvoX - Start Everything
# Usage:  .\start.ps1
# Starts: [1] FastAPI backend on port 8000
#         [2] Telegram bot (polling)

$BACKEND_DIR = "d:\Hackathon\InnovateYou\backend"
$BOT_DIR     = "d:\Hackathon\InnovateYou\telegram-bot-package\bot"
$PYTHON      = "d:\Hackathon\InnovateYou\backend\venv\Scripts\python.exe"
$BOT_TOKEN   = $env:TELEGRAM_BOT_TOKEN
if (-Not $BOT_TOKEN) {
    Write-Host "ERROR: TELEGRAM_BOT_TOKEN env var is not set." -ForegroundColor Red
    Write-Host "Set it first:  `$env:TELEGRAM_BOT_TOKEN='your-token-here'"
    exit 1
}
$BACKEND_URL = "http://localhost:8000"

Write-Host ""
Write-Host "InvoX - Starting all services..." -ForegroundColor Cyan
Write-Host ""

# Kill any existing python processes to avoid port conflicts
Get-Process -Name python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1

# 1. Start backend in a new PowerShell window
$backendCmd = "cd " + $BACKEND_DIR + "; " + `
              "`$env:TELEGRAM_BOT_TOKEN='" + $BOT_TOKEN + "'; " + `
              "`$env:UPLOAD_DIR='uploads'; " + `
              "& '" + $PYTHON + "' -m uvicorn main:app --host 0.0.0.0 --port 8000"
$backendProc = Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd -PassThru
Write-Host "[1] Backend starting (PID $($backendProc.Id)) on http://localhost:8000" -ForegroundColor Green

# Wait for backend to be ready (up to 20s)
Write-Host "    Waiting for backend..." -ForegroundColor DarkGray
$ready = $false
for ($i = 0; $i -lt 20; $i++) {
    Start-Sleep -Seconds 1
    try {
        $null = Invoke-WebRequest -Uri "$BACKEND_URL/openapi.json" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        $ready = $true; break
    } catch {}
}
if ($ready) {
    Write-Host "    Backend is UP!" -ForegroundColor Green
} else {
    Write-Host "    WARNING: Backend not responding - bot may fail." -ForegroundColor Yellow
}

# 2. Start Telegram bot in a new PowerShell window
$botCmd = "`$env:TELEGRAM_BOT_TOKEN='" + $BOT_TOKEN + "'; " + `
          "`$env:BACKEND_URL='" + $BACKEND_URL + "'; " + `
          "`$env:UPLOAD_DIR='" + $BACKEND_DIR + "\uploads'; " + `
          "cd " + $BOT_DIR + "; " + `
          "& '" + $PYTHON + "' invox_bot.py"
$botProc = Start-Process powershell -ArgumentList "-NoExit", "-Command", $botCmd -PassThru
Write-Host "[2] Telegram bot starting (PID $($botProc.Id))" -ForegroundColor Green

Write-Host ""
Write-Host "All services running!" -ForegroundColor Cyan
Write-Host "  Backend  : http://localhost:8000"
Write-Host "  Frontend : cd frontend; npm run dev  (port 3000)"
Write-Host ""
Write-Host "Close the extra terminal windows to stop services." -ForegroundColor DarkGray
