@echo off
setlocal ENABLEDELAYEDEXPANSION

REM Simple non-CMake build for MSVC (Developer Command Prompt)

set ROOT_DIR=%~dp0..\
set BUILD_DIR=%ROOT_DIR%build
set INCLUDE_DIR=%ROOT_DIR%include

if not exist "%BUILD_DIR%" mkdir "%BUILD_DIR%"

where cl >nul 2>nul
if errorlevel 1 (
  echo error: MSVC compiler not found. Please run from "Developer Command Prompt for VS".
  exit /b 1
)

set CXXFLAGS=/std:c++20 /O2 /EHsc /W4 /I "%INCLUDE_DIR%"

set SRC_CODEC=%ROOT_DIR%src\proto\codec.cpp
set SRC_CLIENT=%ROOT_DIR%src\client\weather_client.cpp
set SRC_CLI=%ROOT_DIR%tools\wip_client_cli.cpp
set SRC_TEST=%ROOT_DIR%tests\test_codec.cpp

set OUT_CLI=%BUILD_DIR%\wip_client_cli.exe
set OUT_TEST=%BUILD_DIR%\wiplib_tests.exe

echo [1/2] Building CLI: %OUT_CLI%
cl %CXXFLAGS% "%SRC_CODEC%" "%SRC_CLIENT%" "%SRC_CLI%" /Fe:"%OUT_CLI%" Ws2_32.lib /link /nologo
if errorlevel 1 exit /b 1

echo [2/2] Building tests: %OUT_TEST%
cl %CXXFLAGS% "%SRC_CODEC%" "%SRC_TEST%" /Fe:"%OUT_TEST%" /link /nologo
if errorlevel 1 exit /b 1

echo Done. Binaries in: %BUILD_DIR%
echo Run examples:
echo   %OUT_CLI% --host 127.0.0.1 --port 4110 --area 130010 --weather --temperature
echo   %OUT_TEST%

endlocal

