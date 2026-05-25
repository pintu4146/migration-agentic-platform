@echo off
REM ============================================================================
REM Migration Copilot - Development Environment Setup
REM ============================================================================
REM
REM This script sets up the development environment for the Migration Copilot POC.
REM Run this once before using dev-run.cmd
REM
REM ============================================================================

echo.
echo ============================================================================
echo Migration Copilot - Development Environment Setup
echo ============================================================================
echo.

REM Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH!
    echo.
    echo Please install Python 3.10 or higher from:
    echo https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo [INFO] Python found:
python --version
echo.

REM Create virtual environment if it doesn't exist
if not exist "backend\venv" (
    echo [INFO] Creating virtual environment...
    cd backend
    python -m venv venv
    cd ..
    echo [OK] Virtual environment created
    echo.
) else (
    echo [INFO] Virtual environment already exists
    echo.
)

REM Activate virtual environment and install dependencies
echo [INFO] Installing dependencies...
echo.
cd backend
call venv\Scripts\activate.bat

echo [INFO] Upgrading pip...
python -m pip install --upgrade pip
echo.

echo [INFO] Installing production dependencies...
pip install -r requirements.txt
echo.

echo [INFO] Installing development dependencies...
pip install -r requirements-dev.txt
echo.

cd ..

REM Create .env file if it doesn't exist
if not exist "backend\.env" (
    echo [INFO] Creating .env file from template...
    copy "backend\.env.example" "backend\.env"
    echo.
    echo [ACTION REQUIRED] Please edit backend\.env and add your API keys:
    echo   - OPENAI_API_KEY=your-key-here
    echo   - GEMINI_API_KEY=your-key-here (optional)
    echo   - LANGCHAIN_API_KEY=your-key-here (optional)
    echo.
) else (
    echo [INFO] .env file already exists
    echo.
)

echo ============================================================================
echo Setup Complete!
echo ============================================================================
echo.
echo Next steps:
echo   1. Edit backend\.env and add your API keys
echo   2. Run dev-run.cmd to start the development server
echo.
echo To test the setup:
echo   cd backend
echo   venv\Scripts\activate
echo   python test_imports.py
echo.
pause

@REM Made with Bob
