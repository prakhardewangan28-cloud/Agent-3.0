# PowerShell script to run the backend server

Write-Host "🚀 Starting Knowledge Intelligence Agent Backend..." -ForegroundColor Cyan
Write-Host ""

# Check if virtual environment exists
if (-Not (Test-Path "venv")) {
    Write-Host "❌ Virtual environment not found!" -ForegroundColor Red
    Write-Host "   Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
    Write-Host "   ✓ Virtual environment created" -ForegroundColor Green
}

# Activate virtual environment and check dependencies
Write-Host "📦 Checking dependencies..." -ForegroundColor Cyan
& .\venv\Scripts\Activate.ps1

# Check if requirements are installed
$pipList = pip list
if ($pipList -notmatch "fastapi") {
    Write-Host "   Installing dependencies..." -ForegroundColor Yellow
    pip install -r requirements.txt
    Write-Host "   ✓ Dependencies installed" -ForegroundColor Green
} else {
    Write-Host "   ✓ Dependencies already installed" -ForegroundColor Green
}

# Check if .env file exists
if (-Not (Test-Path ".env")) {
    Write-Host ""
    Write-Host "⚠️  WARNING: .env file not found!" -ForegroundColor Yellow
    Write-Host "   Creating .env from .env.example..." -ForegroundColor Yellow
    Copy-Item .env.example .env
    Write-Host "   ✓ .env file created" -ForegroundColor Green
    Write-Host ""
    Write-Host "   ⚠️  Please edit .env and add your API keys!" -ForegroundColor Yellow
    Write-Host "   Required: SUPABASE_URL, SUPABASE_KEY, SERPAPI_KEY, OPENAI_API_KEY" -ForegroundColor Yellow
    Write-Host ""
}

Write-Host ""
Write-Host "🌐 Starting server on http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "📚 API Documentation: http://127.0.0.1:8000/docs" -ForegroundColor Green
Write-Host "📖 Alternative Docs: http://127.0.0.1:8000/redoc" -ForegroundColor Green
Write-Host ""
Write-Host "Press CTRL+C to stop the server" -ForegroundColor Gray
Write-Host ""

# Start the server
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
