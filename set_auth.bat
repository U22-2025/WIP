@echo off
chcp 65001 >nul
echo =====================================
echo WIP Server Authentication Setting Tool
echo =====================================
echo.

REM Check if .env file exists
if not exist ".env" (
    echo Error: .env file not found
    pause
    exit /b 1
)

REM Function to set environment variable
:setEnvVar
    set "varName=%1"
    set "promptText=%2"

    echo.
    echo Current setting for %promptText%
    powershell -Command "(Get-Content '.env') | Select-String -Pattern '^%varName%='"
    echo.

        SETLOCAL ENABLEDELAYEDEXPANSION
    choice /M "%promptText% (true/false)?" /C:TF
    if errorlevel 2 (
        set "varValue=false"
    ) else (
        set "varValue=true"
    )

    echo Setting %promptText% to !varValue!
    powershell -Command "(Get-Content '.env') | ForEach-Object { $_ -replace '^%varName%=.*', '%varName%=!varValue!%' } | Set-Content '.env.tmp'"
    move ".env.tmp" ".env" >nul
    ENDLOCAL
    exit /b 0

REM Configure each setting
call :setEnvVar WEATHER_SERVER_AUTH_ENABLED "Weather Server Authentication"
call :setEnvVar LOCATION_SERVER_AUTH_ENABLED "Location Server Authentication"
call :setEnvVar QUERY_SERVER_AUTH_ENABLED "Query Server Authentication"
call :setEnvVar REPORT_SERVER_AUTH_ENABLED "Report Server Authentication"
call :setEnvVar WEATHER_SERVER_REQUEST_AUTH_ENABLED "Weather Server Request Authentication"
call :setEnvVar LOCATION_RESOLVER_REQUEST_AUTH_ENABLED "Location Resolver Request Authentication"
call :setEnvVar QUERY_GENERATOR_REQUEST_AUTH_ENABLED "Query Generator Request Authentication"
call :setEnvVar REPORT_SERVER_REQUEST_AUTH_ENABLED "Report Server Request Authentication"

echo.
echo =====================================
echo All server authentication settings updated!
echo =====================================
echo.
echo Please restart servers to apply changes.
echo.
pause