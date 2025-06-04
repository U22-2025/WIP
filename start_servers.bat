@echo off
echo WTPサーバー起動中...

REM 現在のディレクトリを保存
set CURRENT_DIR=%cd%

REM PYTHONPATHを設定（wtpの親ディレクトリを追加）
set PYTHONPATH=%CURRENT_DIR%;%PYTHONPATH%

echo Location Serverを起動中...
start "Servers" cmd /k "cd /d %CURRENT_DIR% && conda activate U22-2025 && python launch_server.py"

echo すべてのサーバーが起動しました。
echo このウィンドウは閉じても大丈夫です。
pause
