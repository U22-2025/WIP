@echo off
echo WIP Server Restart with Unified Authentication
echo ==============================================

echo Setting all required environment variables...

:: 環境変数設定スクリプトを実行
call set_auth_env.bat

echo.
echo Environment variables loaded successfully!
echo.

echo Killing existing server processes...
taskkill /f /im python.exe 2>nul
timeout /t 2 /nobreak >nul

echo.
echo Starting servers with unified authentication...
echo.

:: サーバーを起動
if exist "launch_server.py" (
    echo Starting WIP servers...
    start "WIP Servers" python launch_server.py
    echo Servers started. Please wait a moment for initialization...
    timeout /t 5 /nobreak >nul
) else (
    echo launch_server.py not found. Please start servers manually.
    echo Make sure to use the current environment variables.
)

echo.
echo ================================================
echo All servers should now be running with unified authentication
echo Unified passphrase: %UNIFIED_PASSPHRASE%
echo ================================================