@echo off
REM Quick check if Redis is running and start services

echo.
echo ============================================================
echo   Conversation AI - Service Startup Helper
echo ============================================================
echo.

REM Check if Redis is running
echo [1/3] Checking Redis...
redis-cli ping >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo       ✓ Redis is running
) else (
    echo       ✗ Redis is not running
    echo.
    echo   Options to start Redis:
    echo   1. Docker:  docker run -d -p 6379:6379 redis:7-alpine
    echo   2. Local:   redis-server
    echo   3. Compose: docker-compose up redis -d
    echo.
    echo   Please start Redis first, then run this script again.
    pause
    exit /b 1
)

echo.
echo [2/3] Starting Bot Orchestrator...
echo       Opening in new window...
start "Bot Orchestrator" cmd /k "python scripts\start_orchestrator.py"
timeout /t 3 >nul

echo.
echo [3/3] Starting Agent Worker...
echo       Opening in new window...
start "Agent Worker" cmd /k "python scripts\start_agent_worker.py"

echo.
echo ============================================================
echo   Services Starting!
echo ============================================================
echo.
echo   Two windows should have opened:
echo   - Bot Orchestrator (port 8000)
echo   - Agent Worker (processing queue)
echo.
echo   Wait 5 seconds, then test:
echo   python scripts\test_bot_flow.py
echo.
echo   To stop: Close the service windows or press Ctrl+C in each
echo ============================================================
echo.
pause
