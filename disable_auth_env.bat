@echo off
echo WIP Authentication System - Disable Authentication
echo ====================================================

echo Disabling authentication for all servers...

:: Weather Server
set WEATHER_SERVER_AUTH_ENABLED=false
set WEATHER_SERVER_PASSPHRASE=

:: Location Resolver
set LOCATION_SERVER_AUTH_ENABLED=false
set LOCATION_SERVER_PASSPHRASE=

:: Query Generator  
set QUERY_SERVER_AUTH_ENABLED=false
set QUERY_SERVER_PASSPHRASE=

:: Report Server
set REPORT_SERVER_AUTH_ENABLED=false
set REPORT_SERVER_PASSPHRASE=

echo.
echo Authentication has been disabled for all servers!
echo.
echo Current authentication settings:
echo   Weather Server: %WEATHER_SERVER_AUTH_ENABLED%
echo   Location Resolver: %LOCATION_SERVER_AUTH_ENABLED%
echo   Query Generator: %QUERY_SERVER_AUTH_ENABLED%
echo   Report Server: %REPORT_SERVER_AUTH_ENABLED%
echo.
echo Note: These settings are only valid for the current command session
echo ====================================================