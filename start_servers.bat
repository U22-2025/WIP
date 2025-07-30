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

wt ^
  new-tab cmd /k "cd /d %CURRENT_DIR% && python python/launch_server.py --weather" ^
  ; split-pane -V cmd /k "cd /d %CURRENT_DIR%  && python python/launch_server.py --query" ^
  ; focus-pane -t 0 ^
  ; split-pane -H cmd /k "cd /d %CURRENT_DIR% && python python/launch_server.py --location" ^
  ; focus-pane -t 1 ^
  ; split-pane -H cmd /k "cd /d %CURRENT_DIR% && python python/launch_server.py --report" ^
  ; split-pane -V cmd /k "cd /d %CURRENT_DIR% && python python/application/map/start_fastapi_server.py" ^
start http://localhost:5000

echo すべてのサーバーが起動しました。