@echo off
chcp 65001 >nul
echo =====================================
echo WIP Server Individual Authentication Setting Tool
echo =====================================
echo.

REM Check if .env file exists
if not exist ".env" (
    echo Error: .env file not found
    pause
    exit /b 1
)

:menu
cls
echo =====================================
echo WIP Server Individual Authentication Settings
echo =====================================
echo.
echo 現在の設定:
echo.
powershell -Command "(Get-Content '.env') | Select-String -Pattern '^WEATHER_SERVER_AUTH_ENABLED=|^LOCATION_SERVER_AUTH_ENABLED=|^QUERY_SERVER_AUTH_ENABLED=|^REPORT_SERVER_AUTH_ENABLED=|^WEATHER_SERVER_REQUEST_AUTH_ENABLED=|^LOCATION_RESOLVER_REQUEST_AUTH_ENABLED=|^QUERY_GENERATOR_REQUEST_AUTH_ENABLED=|^REPORT_SERVER_REQUEST_AUTH_ENABLED='"
echo.
echo 個別設定メニュー:
echo.
echo 1. Weather Server Authentication
echo 2. Location Server Authentication  
echo 3. Query Server Authentication
echo 4. Report Server Authentication
echo 5. Weather Server Request Authentication
echo 6. Location Resolver Request Authentication
echo 7. Query Generator Request Authentication
echo 8. Report Server Request Authentication
echo.
echo 9. 全ての認証を有効化
echo 0. 全ての認証を無効化
echo.
echo q. 終了
echo.
set /p choice="選択してください (1-9, 0, q): "

if /i "%choice%"=="q" goto :end
if "%choice%"=="1" goto :weather_server
if "%choice%"=="2" goto :location_server
if "%choice%"=="3" goto :query_server
if "%choice%"=="4" goto :report_server
if "%choice%"=="5" goto :weather_request
if "%choice%"=="6" goto :location_request
if "%choice%"=="7" goto :query_request
if "%choice%"=="8" goto :report_request
if "%choice%"=="9" goto :enable_all
if "%choice%"=="0" goto :disable_all

echo 無効な選択です。
pause
goto :menu

:weather_server
call :setSingleVar "WEATHER_SERVER_AUTH_ENABLED" "Weather Server Authentication"
goto :menu

:location_server
call :setSingleVar "LOCATION_SERVER_AUTH_ENABLED" "Location Server Authentication"
goto :menu

:query_server
call :setSingleVar "QUERY_SERVER_AUTH_ENABLED" "Query Server Authentication"
goto :menu

:report_server
call :setSingleVar "REPORT_SERVER_AUTH_ENABLED" "Report Server Authentication"
goto :menu

:weather_request
call :setSingleVar "WEATHER_SERVER_REQUEST_AUTH_ENABLED" "Weather Server Request Authentication"
goto :menu

:location_request
call :setSingleVar "LOCATION_RESOLVER_REQUEST_AUTH_ENABLED" "Location Resolver Request Authentication"
goto :menu

:query_request
call :setSingleVar "QUERY_GENERATOR_REQUEST_AUTH_ENABLED" "Query Generator Request Authentication"
goto :menu

:report_request
call :setSingleVar "REPORT_SERVER_REQUEST_AUTH_ENABLED" "Report Server Request Authentication"
goto :menu

:enable_all
echo.
echo 全ての認証を有効化しています...
powershell -Command "(Get-Content '.env') | ForEach-Object { $_ -replace '^WEATHER_SERVER_AUTH_ENABLED=.*', 'WEATHER_SERVER_AUTH_ENABLED=true' -replace '^LOCATION_SERVER_AUTH_ENABLED=.*', 'LOCATION_SERVER_AUTH_ENABLED=true' -replace '^QUERY_SERVER_AUTH_ENABLED=.*', 'QUERY_SERVER_AUTH_ENABLED=true' -replace '^REPORT_SERVER_AUTH_ENABLED=.*', 'REPORT_SERVER_AUTH_ENABLED=true' -replace '^WEATHER_SERVER_REQUEST_AUTH_ENABLED=.*', 'WEATHER_SERVER_REQUEST_AUTH_ENABLED=true' -replace '^LOCATION_RESOLVER_REQUEST_AUTH_ENABLED=.*', 'LOCATION_RESOLVER_REQUEST_AUTH_ENABLED=true' -replace '^QUERY_GENERATOR_REQUEST_AUTH_ENABLED=.*', 'QUERY_GENERATOR_REQUEST_AUTH_ENABLED=true' -replace '^REPORT_SERVER_REQUEST_AUTH_ENABLED=.*', 'REPORT_SERVER_REQUEST_AUTH_ENABLED=true' } | Set-Content '.env'"
echo 全ての認証が有効化されました。
echo.
pause
goto :menu

:disable_all
echo.
echo 全ての認証を無効化しています...
powershell -Command "(Get-Content '.env') | ForEach-Object { $_ -replace '^WEATHER_SERVER_AUTH_ENABLED=.*', 'WEATHER_SERVER_AUTH_ENABLED=false' -replace '^LOCATION_SERVER_AUTH_ENABLED=.*', 'LOCATION_SERVER_AUTH_ENABLED=false' -replace '^QUERY_SERVER_AUTH_ENABLED=.*', 'QUERY_SERVER_AUTH_ENABLED=false' -replace '^REPORT_SERVER_AUTH_ENABLED=.*', 'REPORT_SERVER_AUTH_ENABLED=false' -replace '^WEATHER_SERVER_REQUEST_AUTH_ENABLED=.*', 'WEATHER_SERVER_REQUEST_AUTH_ENABLED=false' -replace '^LOCATION_RESOLVER_REQUEST_AUTH_ENABLED=.*', 'LOCATION_RESOLVER_REQUEST_AUTH_ENABLED=false' -replace '^QUERY_GENERATOR_REQUEST_AUTH_ENABLED=.*', 'QUERY_GENERATOR_REQUEST_AUTH_ENABLED=false' -replace '^REPORT_SERVER_REQUEST_AUTH_ENABLED=.*', 'REPORT_SERVER_REQUEST_AUTH_ENABLED=false' } | Set-Content '.env'"
echo 全ての認証が無効化されました。
echo.
pause
goto :menu

:setSingleVar
SETLOCAL ENABLEDELAYEDEXPANSION
set "varName=%~1"
set "promptText=%~2"

echo.
echo 現在の設定: %promptText%
powershell -Command "(Get-Content '.env') | Select-String -Pattern '^%varName%='"
echo.

choice /M "%promptText% を有効化しますか (true/false)?" /C:TF
if errorlevel 2 (
    set "varValue=false"
) else (
    set "varValue=true"
)

echo %promptText% を !varValue! に設定しています...
powershell -Command "(Get-Content '.env') | ForEach-Object { $_ -replace '^%varName%=.*', '%varName%=!varValue!' } | Set-Content '.env'"
echo 設定が完了しました。
echo.
pause
ENDLOCAL
exit /b 0

:end
echo.
echo 設定を完了しました。
echo サーバーを再起動して変更を適用してください。
echo.
pause