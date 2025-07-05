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

:: Unified Server Receive Passphrase
set WIP_SERVER_RECEIVE_PASSPHRASE=wip_unified_receive_key_2024

:: Location Server -> Other Servers Authentication
set LOCATION_TO_WEATHER_AUTH_ENABLED=true
set LOCATION_TO_WEATHER_PASSPHRASE=location_to_weather_key_2024
set LOCATION_TO_QUERY_AUTH_ENABLED=true
set LOCATION_TO_QUERY_PASSPHRASE=location_to_query_key_2024
set LOCATION_TO_REPORT_AUTH_ENABLED=true
set LOCATION_TO_REPORT_PASSPHRASE=location_to_report_key_2024

:: Query Server -> Other Servers Authentication
set QUERY_TO_LOCATION_AUTH_ENABLED=true
set QUERY_TO_LOCATION_PASSPHRASE=query_to_location_key_2024
set QUERY_TO_WEATHER_AUTH_ENABLED=true
set QUERY_TO_WEATHER_PASSPHRASE=query_to_weather_key_2024
set QUERY_TO_REPORT_AUTH_ENABLED=true
set QUERY_TO_REPORT_PASSPHRASE=query_to_report_key_2024

:: Report Server -> Other Servers Authentication
set REPORT_TO_LOCATION_AUTH_ENABLED=true
set REPORT_TO_LOCATION_PASSPHRASE=report_to_location_key_2024
set REPORT_TO_WEATHER_AUTH_ENABLED=true
set REPORT_TO_WEATHER_PASSPHRASE=report_to_weather_key_2024
set REPORT_TO_QUERY_AUTH_ENABLED=true
set REPORT_TO_QUERY_PASSPHRASE=report_to_query_key_2024

:: Weather Server -> Other Servers Authentication
set WEATHER_TO_LOCATION_AUTH_ENABLED=true
set WEATHER_TO_LOCATION_PASSPHRASE=weather_to_location_key_2024
set WEATHER_TO_QUERY_AUTH_ENABLED=true
set WEATHER_TO_QUERY_PASSPHRASE=weather_to_query_key_2024
set WEATHER_TO_REPORT_AUTH_ENABLED=true
set WEATHER_TO_REPORT_PASSPHRASE=weather_to_report_key_2024

echo.
echo Authentication environment variables have been set successfully!
echo.
echo Current authentication settings:
echo   Weather Server: %WEATHER_SERVER_AUTH_ENABLED% (Passphrase: %WEATHER_SERVER_PASSPHRASE%)
echo   Location Resolver: %LOCATION_RESOLVER_AUTH_ENABLED% (Passphrase: %LOCATION_RESOLVER_PASSPHRASE%)
echo   Query Generator: %QUERY_GENERATOR_AUTH_ENABLED% (Passphrase: %QUERY_GENERATOR_PASSPHRASE%)
echo   Report Server: %REPORT_SERVER_AUTH_ENABLED% (Passphrase: %REPORT_SERVER_PASSPHRASE%)
echo.
echo   Unified Receive Passphrase: %WIP_SERVER_RECEIVE_PASSPHRASE%
echo.
echo Server-to-Server Request Authentication:
echo   Location -> Weather: %LOCATION_TO_WEATHER_AUTH_ENABLED% (%LOCATION_TO_WEATHER_PASSPHRASE%)
echo   Location -> Query: %LOCATION_TO_QUERY_AUTH_ENABLED% (%LOCATION_TO_QUERY_PASSPHRASE%)
echo   Location -> Report: %LOCATION_TO_REPORT_AUTH_ENABLED% (%LOCATION_TO_REPORT_PASSPHRASE%)
echo   Query -> Location: %QUERY_TO_LOCATION_AUTH_ENABLED% (%QUERY_TO_LOCATION_PASSPHRASE%)
echo   Query -> Weather: %QUERY_TO_WEATHER_AUTH_ENABLED% (%QUERY_TO_WEATHER_PASSPHRASE%)
echo   Query -> Report: %QUERY_TO_REPORT_AUTH_ENABLED% (%QUERY_TO_REPORT_PASSPHRASE%)
echo   Report -> Location: %REPORT_TO_LOCATION_AUTH_ENABLED% (%REPORT_TO_LOCATION_PASSPHRASE%)
echo   Report -> Weather: %REPORT_TO_WEATHER_AUTH_ENABLED% (%REPORT_TO_WEATHER_PASSPHRASE%)
echo   Report -> Query: %REPORT_TO_QUERY_AUTH_ENABLED% (%REPORT_TO_QUERY_PASSPHRASE%)
echo   Weather -> Location: %WEATHER_TO_LOCATION_AUTH_ENABLED% (%WEATHER_TO_LOCATION_PASSPHRASE%)
echo   Weather -> Query: %WEATHER_TO_QUERY_AUTH_ENABLED% (%WEATHER_TO_QUERY_PASSPHRASE%)
echo   Weather -> Report: %WEATHER_TO_REPORT_AUTH_ENABLED% (%WEATHER_TO_REPORT_PASSPHRASE%)
echo.
echo Note: These settings are only valid for the current command session
echo =========================================================