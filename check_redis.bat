@echo off
REM Simple Redis status checker

echo.
echo ============================================================
echo   Redis Status Check
echo ============================================================
echo.

redis-cli ping >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo ✓ Redis is RUNNING
    echo.
    
    REM Get some info
    echo Info:
    for /f "tokens=*" %%i in ('redis-cli info server ^| findstr "redis_version"') do echo   %%i
    for /f "tokens=*" %%i in ('redis-cli info clients ^| findstr "connected_clients"') do echo   %%i
    echo.
    
    REM Check queue
    echo Queue status:
    python scripts\check_redis.py
) else (
    echo ✗ Redis is NOT running
    echo.
    echo To start Redis:
    echo   Option 1 - Docker:
    echo     docker run -d --name redis -p 6379:6379 redis:7-alpine
    echo.
    echo   Option 2 - Docker Compose:
    echo     docker-compose up redis -d
    echo.
    echo   Option 3 - Local Install:
    echo     redis-server
    echo.
)

echo.
pause
