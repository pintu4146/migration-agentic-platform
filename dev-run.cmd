@echo off
REM ============================================================================
REM Migration Copilot - Development Server Launcher
REM ============================================================================
REM
REM This script starts the development server for the Migration Copilot POC.
REM It will be updated as we progress through implementation phases.
REM
REM Current Phase: Phase 1 - Foundation
REM ============================================================================

echo.
echo ============================================================================
echo Migration Copilot - Development Server
echo ============================================================================
echo.
echo Current Phase: Phase 1 - Foundation
echo.

REM Check if virtual environment exists
if not exist "backend\venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found!
    echo.
    echo Please run setup first:
    echo   cd backend
    echo   python -m venv venv
    echo   venv\Scripts\activate
    echo   pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

REM Check if .env file exists
if not exist "backend\.env" (
    echo [WARNING] .env file not found!
    echo.
    echo Creating .env from .env.example...
    copy "backend\.env.example" "backend\.env"
    echo.
    echo [ACTION REQUIRED] Please edit backend\.env and add your API keys:
    echo   - OPENAI_API_KEY
    echo   - GEMINI_API_KEY (optional)
    echo   - LANGCHAIN_API_KEY (optional)
    echo.
    pause
)

echo [INFO] Starting backend server...
echo.
echo Server will be available at:
echo   - API: http://localhost:8000
echo   - Docs: http://localhost:8000/docs
echo   - ReDoc: http://localhost:8000/redoc
echo.
echo Press Ctrl+C to stop the server
echo.
echo ============================================================================
echo.

REM Change to backend directory and start server
cd backend
call venv\Scripts\activate.bat
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

REM If server stops, pause to show any errors
echo.
echo ============================================================================
echo Server stopped
echo ============================================================================
pause

@REM Made with Bob
