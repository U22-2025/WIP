@echo off
chcp 65001 > nul
echo WIPサーバー起動中...

set CURRENT_DIR=%cd%
set PYTHONPATH=%CURRENT_DIR%;%PYTHONPATH%

wt ^
  new-tab cmd /k "cd /d %CURRENT_DIR% && conda activate U22-2025 && python python/launch_server.py --weather --debug" ^
  ; split-pane -V cmd /k "cd /d %CURRENT_DIR% && conda activate U22-2025 && python python/launch_server.py --query --debug" ^
  ; focus-pane -t 0 ^
  ; split-pane -H cmd /k "cd /d %CURRENT_DIR% && conda activate U22-2025 && python python/launch_server.py --location --debug" ^
  ; focus-pane -t 1 ^
  ; split-pane -H cmd /k "cd /d %CURRENT_DIR% && conda activate U22-2025 && python python/launch_server.py --report --debug" ^
  ; split-pane -V cmd /k "cd /d %CURRENT_DIR%/python/application/map && conda activate U22-2025 && python app.py"

start http://localhost

echo すべてのサーバーが起動しました。