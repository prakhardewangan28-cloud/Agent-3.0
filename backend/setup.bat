@echo off
echo ========================================
echo Backend Setup Script
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.11+ from https://python.org
    pause
    exit /b 1
)

echo Step 1: Creating virtual environment...
if not exist "venv" (
    python -m venv venv
    echo Virtual environment created
) else (
    echo Virtual environment already exists
)
echo.

echo Step 2: Activating virtual environment...
call venv\Scripts\activate.bat
echo.

echo Step 3: Upgrading pip...
python -m pip install --upgrade pip
echo.

echo Step 4: Installing dependencies from requirements.txt...
pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo.

echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo To activate the virtual environment, run:
echo   venv\Scripts\activate
echo.
echo To run tests:
echo   run_tests.bat
echo.
echo To check environment:
echo   python scripts\check_env.py
echo.
pause
