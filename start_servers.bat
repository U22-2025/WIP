@echo off
echo WTPサーバー起動中...

REM 現在のディレクトリを保存
set CURRENT_DIR=%cd%

REM PYTHONPATHを設定（wtpの親ディレクトリを追加）
set PYTHONPATH=%CURRENT_DIR%;%PYTHONPATH%

echo Location Serverを起動中...
start "Location Server" cmd /k "cd /d %CURRENT_DIR% && conda activate U22-2025 && python -m wtp.servers.location_server.location_server"

echo Query Serverを起動中...
start "Query Server" cmd /k "cd /d %CURRENT_DIR% && conda activate U22-2025 && python -m wtp.servers.query_server.query_server"

echo Weather Serverを起動中...
start "Weather Server" cmd /k "cd /d %CURRENT_DIR% && conda activate U22-2025 && python -m wtp.servers.weather_server.weather_server"

echo すべてのサーバーが起動しました。
echo このウィンドウは閉じても大丈夫です。
pause
