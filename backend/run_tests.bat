@echo off
echo ========================================
echo Running Tests
echo ========================================
echo.

REM Check if venv exists
if not exist "venv" (
    echo ERROR: Virtual environment not found
    echo Please run setup.bat first
    pause
    exit /b 1
)

REM Activate venv
call venv\Scripts\activate.bat

REM Run pytest
echo Running pytest...
echo.
pytest -v
if errorlevel 1 (
    echo.
    echo ========================================
    echo TESTS FAILED
    echo ========================================
    pause
    exit /b 1
) else (
    echo.
    echo ========================================
    echo ALL TESTS PASSED
    echo ========================================
    pause
)
