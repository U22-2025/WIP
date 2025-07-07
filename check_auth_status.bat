@echo off
chcp 65001 >nul
echo =====================================
echo WIP Server Authentication Status Check
echo =====================================
echo.

REM Check if .env file exists
if not exist ".env" (
    echo Error: .env file not found
    pause
    exit /b 1
)

echo Current authentication settings:
echo.
echo [Server Authentication Settings]
for /f "tokens=1,2 delims==" %%A in ('findstr "AUTH_ENABLED" .env ^| findstr /v "REQUEST"') do (
    echo %%A = %%B
)

echo.
echo [Request Authentication Settings]
for /f "tokens=1,2 delims==" %%A in ('findstr "REQUEST_AUTH_ENABLED" .env') do (
    echo %%A = %%B
)

echo.
echo [Passphrase Settings]
for /f "tokens=1,2 delims==" %%A in ('findstr "PASSPHRASE" .env') do (
    echo %%A = %%B
)

echo.
echo =====================================
echo Authentication status check complete
echo =====================================
echo.
echo Available tools:
echo - enable_all_auth.bat  : Enable all authentication
echo - disable_all_auth.bat : Disable all authentication  
echo - check_auth_status.bat: Check current settings
echo.
pause