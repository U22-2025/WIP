@echo off
REM JMA Weather API Integration Test Runner for Windows

echo JMA Weather API Integration Test Runner
echo ========================================

REM 現在のディレクトリ設定
cd /d "%~dp0\.."

REM 環境変数設定
set PYTHONPATH=%CD%\src;%PYTHONPATH%

REM 設定可能な変数
set WEATHER_API_PORT=8001
set REPORT_SERVER_PORT=9999
set TEST_MODE=%1

if "%TEST_MODE%"=="" set TEST_MODE=simple

echo Configuration:
echo   Weather API Port: %WEATHER_API_PORT%
echo   Report Server Port: %REPORT_SERVER_PORT%
echo   Test Mode: %TEST_MODE%
echo   Python Path: %PYTHONPATH%
echo.

REM Redis接続確認
echo Checking Redis connection...
redis-cli ping >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Redis is not running
    echo Please start Redis server first:
    echo   redis-server
    echo.
    pause
    exit /b 1
)
echo ✅ Redis is running
echo.

REM Weather API Server確認
echo Checking Weather API Server...
curl -s http://localhost:%WEATHER_API_PORT%/health >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ⚠️  Weather API Server not detected on port %WEATHER_API_PORT%
    echo To start Weather API Server:
    echo   cd python\application\weather_api
    echo   python start_server.py
    echo.
    echo Some tests will be skipped without the API server.
    echo.
) else (
    echo ✅ Weather API Server is running
    echo.
)

REM テストモードに応じて実行
if "%TEST_MODE%"=="simple" (
    echo Running Simple Integration Test...
    echo ===================================
    python tests\test_jma_api_simple.py --api-port %WEATHER_API_PORT% --report-port %REPORT_SERVER_PORT% --debug
) else if "%TEST_MODE%"=="full" (
    echo Running Full Integration Test...
    echo ===============================
    python -m pytest tests\test_jma_full_integration.py -v
) else if "%TEST_MODE%"=="both" (
    echo Running Both Tests...
    echo ====================
    echo.
    echo 1. Simple Test:
    python tests\test_jma_api_simple.py --api-port %WEATHER_API_PORT% --report-port %REPORT_SERVER_PORT%
    echo.
    echo 2. Full Test:
    python -m pytest tests\test_jma_full_integration.py -v
) else (
    echo Invalid test mode: %TEST_MODE%
    echo Valid modes: simple, full, both
    exit /b 1
)

REM 結果確認
if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ Tests completed successfully!
    echo.
    echo Data flow verified:
    echo   JMA → Weather API → Report Client → Report Server → Redis
) else (
    echo.
    echo ❌ Tests failed with exit code %ERRORLEVEL%
    echo Please check the error messages above.
)

echo.
pause