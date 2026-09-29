@echo off
REM Quick Setup Script for Windows
echo ========================================
echo Track 5 Hackathon Backend - Quick Setup
echo ========================================
echo.

REM Check Python
echo [1/5] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.11+ from python.org
    pause
    exit /b 1
)
python --version
echo.

REM Create virtual environment
echo [2/5] Creating virtual environment...
if exist venv (
    echo Virtual environment already exists, skipping...
) else (
    python -m venv venv
    echo Virtual environment created!
)
echo.

REM Activate and install dependencies
echo [3/5] Installing dependencies...
call venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt
echo.

REM Copy .env.example to .env if it doesn't exist
echo [4/5] Setting up environment file...
if exist .env (
    echo .env already exists, skipping...
) else (
    copy .env.example .env
    echo.
    echo ========================================
    echo IMPORTANT: Edit .env file now!
    echo ========================================
    echo Add your actual API keys to the .env file before proceeding.
    echo.
    echo Keys needed:
    echo - Supabase URL and Key: https://supabase.com/dashboard
    echo - SerpAPI Key: https://serpapi.com/manage-api-key  
    echo - Gemini API Key: https://aistudio.google.com/apikey
    echo.
    pause
)
echo.

REM Run verification
echo [5/5] Running verification tests...
echo.
python scripts/check_env.py
echo.

echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Make sure all API keys are configured in .env
echo 2. Run: python scripts/check_gemini.py
echo 3. Run: python scripts/check_db.py
echo 4. Run: python scripts/check_serpapi.py
echo 5. Start server: uvicorn app.main:app --reload
echo.
echo Need help? Read SETUP.md for detailed instructions.
echo.
pause
