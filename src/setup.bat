@echo off
REM Quick setup script for Conversational AI

echo ========================================
echo   Conversational AI - Quick Setup
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Please install Python 3.8 or higher.
    pause
    exit /b 1
)

echo [1/4] Python found
echo.

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo [2/4] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
) else (
    echo [2/4] Virtual environment exists
)
echo.

REM Activate virtual environment
echo [3/4] Activating virtual environment...
call venv\Scripts\activate.bat
echo.

REM Install dependencies
echo [4/4] Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)
echo.

REM Copy .env.example if .env doesn't exist
if not exist ".env" (
    echo Copying .env.example to .env...
    copy .env.example .env
    echo.
    echo [IMPORTANT] Please edit .env and add your API keys:
    echo   - FAL_KEY from https://fal.ai/dashboard
    echo   - OPENROUTER_KEY from https://openrouter.ai/keys
    echo.
    notepad .env
)

echo.
echo ========================================
echo   Setup Complete!
echo ========================================
echo.
echo Next steps:
echo   1. Make sure your API keys are set in .env
echo   2. Run: python main.py --vad
echo.
echo Test commands:
echo   python main.py --info          (show config)
echo   python main.py --vad            (voice mode)
echo   python main.py --manual         (manual mode)
echo   python main.py --duration 3     (quick test)
echo.
pause
