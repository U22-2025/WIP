@echo off
chcp 65001 > nul
echo WIPサーバー起動中...

set CURRENT_DIR=%cd%
set PYTHONPATH=%CURRENT_DIR%;%PYTHONPATH%

@REM wt ^
@REM   new-tab cmd /k "cd /d %CURRENT_DIR% && conda activate U22-WIP && python python/launch_server.py --weather --debug" ^
@REM   ; split-pane -V cmd /k "cd /d %CURRENT_DIR% && conda activate U22-WIP && python python/launch_server.py --query --debug --noupdate" ^
@REM   ; focus-pane -t 0 ^
@REM   ; split-pane -H cmd /k "cd /d %CURRENT_DIR% && conda activate U22-WIP && python python/launch_server.py --location --debug" ^
@REM   ; focus-pane -t 1 ^
@REM   ; split-pane -H cmd /k "cd /d %CURRENT_DIR% && conda activate U22-WIP && python python/launch_server.py --report --debug" ^
@REM   ; split-pane -V cmd /k "cd /d %CURRENT_DIR% && conda activate U22-WIP && python python/application/map/start_fastapi_server.py --debug" ^

@REM 通常のstartコマンドを使用してサーバーを個別ウィンドウで起動
start "Weather Server" cmd /k "cd /d %CURRENT_DIR% && python python/launch_server.py --weather"
timeout /t 2 /nobreak > nul
start "Query Server" cmd /k "cd /d %CURRENT_DIR% && python python/launch_server.py --query"
timeout /t 2 /nobreak > nul
start "Location Server" cmd /k "cd /d %CURRENT_DIR% && python python/launch_server.py --location"
timeout /t 2 /nobreak > nul
start "Report Server" cmd /k "cd /d %CURRENT_DIR% && python python/launch_server.py --report --debug"
timeout /t 2 /nobreak > nul
start "Map FastAPI Server" cmd /k "cd /d %CURRENT_DIR% && python python/application/map/start_fastapi_server.py"
timeout /t 2 /nobreak > nul
start "Weather API Server" cmd /k "cd /d %CURRENT_DIR% && python python/application/weather_api/start_fastapi_server.py" ^
start http://localhost:5000

echo すべてのサーバーが起動しました。
