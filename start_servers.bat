@echo off
chcp 65001 > nul
echo WTPサーバー起動中...

REM 現在のディレクトリを保存
set CURRENT_DIR=%cd%

REM PYTHONPATHを設定（wtpの親ディレクトリを追加）
set PYTHONPATH=%CURRENT_DIR%;%PYTHONPATH%

echo 全Serverを起動中...
@REM start "Servers" cmd /k "cd /d %CURRENT_DIR% && conda activate U22-2025 && python launch_server.py --debug"

echo Location Serverを起動中
start "Location Server" cmd /k "cd /d %CURRENT_DIR% && conda activate U22-2025 && python launch_server.py --location --debug"

echo Weather Serverを起動中
start "Weather Server" cmd /k "cd /d %CURRENT_DIR% && conda activate U22-2025 && python launch_server.py --weather --debug"

echo Query Serverを起動中
start "Query Server" cmd /k "cd /d %CURRENT_DIR% && conda activate U22-2025 && python launch_server.py --query --debug"

echo MAP Serverを起動中
start "MAP Server" cmd /k "cd /d %CURRENT_DIR% && conda activate U22-2025 && cd application/map/ &&  python app.py"


echo すべてのサーバーが起動しました。
pause