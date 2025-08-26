@echo off
REM Weather API Server Startup Script for Windows

echo Weather API Server Startup
echo =============================

REM 現在のディレクトリに移動
cd /d "%~dp0"

REM 環境変数設定（必要に応じて変更）
set WEATHER_API_PORT=8001
set WEATHER_API_HOST=0.0.0.0
set WEATHER_API_RELOAD=false
set WEATHER_API_TARGET_OFFICES=130000,270000,011000,400000,230000

echo Current directory: %CD%
echo Port: %WEATHER_API_PORT%
echo Target offices: %WEATHER_API_TARGET_OFFICES%
echo.

REM PYTHONPATHを設定
set PYTHONPATH=%CD%\..\..\..\src;%CD%;%PYTHONPATH%
echo Python path: %PYTHONPATH%
echo.

REM Pythonサーバー起動
echo Starting Weather API Server...
python run_server.py

REM エラー時の確認
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Server startup failed with exit code %ERRORLEVEL%
    echo Please check the error messages above.
    pause
)