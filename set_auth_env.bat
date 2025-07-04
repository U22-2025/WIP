@echo off
echo WIP Authentication System - Environment Variables Setup
echo =========================================================

echo Setting authentication environment variables...

:: Weather Server
set WEATHER_SERVER_AUTH_ENABLED=true
set WEATHER_SERVER_PASSPHRASE=weather_secure_key_2024

:: Location Resolver
set LOCATION_RESOLVER_AUTH_ENABLED=true
set LOCATION_RESOLVER_PASSPHRASE=location_secure_key_2024

:: Query Generator  
set QUERY_GENERATOR_AUTH_ENABLED=true
set QUERY_GENERATOR_PASSPHRASE=query_secure_key_2024

:: Report Server
set REPORT_SERVER_AUTH_ENABLED=true
set REPORT_SERVER_PASSPHRASE=report_secure_key_2024

echo.
echo Authentication environment variables have been set successfully!
echo.
echo Current authentication settings:
echo   Weather Server: %WEATHER_SERVER_AUTH_ENABLED% (Passphrase: %WEATHER_SERVER_PASSPHRASE%)
echo   Location Resolver: %LOCATION_RESOLVER_AUTH_ENABLED% (Passphrase: %LOCATION_RESOLVER_PASSPHRASE%)
echo   Query Generator: %QUERY_GENERATOR_AUTH_ENABLED% (Passphrase: %QUERY_GENERATOR_PASSPHRASE%)
echo   Report Server: %REPORT_SERVER_AUTH_ENABLED% (Passphrase: %REPORT_SERVER_PASSPHRASE%)
echo.
echo Note: These settings are only valid for the current command session
echo =========================================================