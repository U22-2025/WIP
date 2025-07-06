@echo off
echo WIP System - Complete Environment Variables Setup
echo =========================================================

echo Setting all required environment variables...

:: ============================================
:: Server Port Settings
:: ============================================
set WEATHER_SERVER_PORT=4110
set LOCATION_RESOLVER_PORT=4109
set QUERY_GENERATOR_PORT=4111
set REPORT_SERVER_PORT=4112

:: ============================================
:: Server Host Settings
:: ============================================
set LOCATION_RESOLVER_HOST=localhost
set QUERY_GENERATOR_HOST=localhost
set REPORT_SERVER_HOST=localhost

:: ============================================
:: System Settings
:: ============================================
set WIP_DEBUG=true
set PROTOCOL_VERSION=1
set UDP_BUFFER_SIZE=4096

:: ============================================
:: Database Settings (PostgreSQL)
:: ============================================
set DB_HOST=localhost
set DB_PORT=5432
set DB_NAME=wip_weather
set DB_USERNAME=wip_user
set DB_PASSWORD=wip_password

:: ============================================
:: Redis Settings
:: ============================================
set REDIS_HOST=localhost
set REDIS_PORT=6379

:: ============================================
:: Cache and Storage Settings
:: ============================================
set MAX_CACHE_SIZE=1000
set WEATHER_OUTPUT_FILE=wip/json/weather_data.json

:: ============================================
:: Authentication Settings
:: ============================================

:: Weather Server
set WEATHER_SERVER_AUTH_ENABLED=true
set WEATHER_SERVER_PASSPHRASE=secure_key_2024

:: Location Resolver
set LOCATION_SERVER_AUTH_ENABLED=true
set LOCATION_SERVER_PASSPHRASE=secure_key_2024

:: Query Generator
set QUERY_SERVER_AUTH_ENABLED=true
set QUERY_SERVER_PASSPHRASE=secure_key_2024

:: Report Server
set REPORT_SERVER_AUTH_ENABLED=true
set REPORT_SERVER_PASSPHRASE=secure_key_2024

:: Server Request Authentication Settings
:: ここは各サーバが上部の~_SERVER_AUTH_ENABLEDをtrueにしていれば、他サーバもtrueにする必要がある
set WEATHER_SERVER_REQUEST_AUTH_ENABLED=true
set LOCATION_RESOLVER_REQUEST_AUTH_ENABLED=true
set QUERY_GENERATOR_REQUEST_AUTH_ENABLED=true
set REPORT_SERVER_REQUEST_AUTH_ENABLED=true

:: Response Authentication Settings
set WEATHER_SERVER_RESPONSE_AUTH_ENABLED=true
set LOCATION_RESOLVER_RESPONSE_AUTH_ENABLED=true
set QUERY_GENERATOR_RESPONSE_AUTH_ENABLED=true
set REPORT_SERVER_RESPONSE_AUTH_ENABLED=true

echo.
echo =========================================================
echo All environment variables have been set successfully!
echo =========================================================
echo.
echo Server Configuration:
echo   Weather Server: %WEATHER_SERVER_PORT% (Auth: %WEATHER_SERVER_AUTH_ENABLED%)
echo   Location Resolver: %LOCATION_RESOLVER_HOST%:%LOCATION_RESOLVER_PORT% (Auth: %LOCATION_SERVER_AUTH_ENABLED%)
echo   Query Generator: %QUERY_GENERATOR_HOST%:%QUERY_GENERATOR_PORT% (Auth: %QUERY_SERVER_AUTH_ENABLED%)
echo   Report Server: %REPORT_SERVER_HOST%:%REPORT_SERVER_PORT% (Auth: %REPORT_SERVER_AUTH_ENABLED%)
echo.
echo Database Configuration:
echo   PostgreSQL: %DB_HOST%:%DB_PORT%/%DB_NAME%
echo   Redis: %REDIS_HOST%:%REDIS_PORT%
echo.
echo System Configuration:
echo   Debug Mode: %WIP_DEBUG%
echo   Protocol Version: %PROTOCOL_VERSION%
echo   UDP Buffer Size: %UDP_BUFFER_SIZE%
echo.
echo Note: These settings are only valid for the current command session
echo Note: For persistent settings, configure system environment variables
echo =========================================================