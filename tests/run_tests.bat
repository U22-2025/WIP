@echo off
REM WTP Packet テストスイート実行バッチファイル (Windows用)

echo WTP Packet テストスイート
echo ========================

REM 引数がない場合はヘルプを表示
if "%1"=="" (
    echo 使用方法:
    echo   run_tests.bat unit          - ユニットテストを実行
    echo   run_tests.bat integration   - 統合テストを実行
    echo   run_tests.bat all           - 全テストを実行
    echo   run_tests.bat quick         - クイックテストを実行
    echo   run_tests.bat coverage      - カバレッジ付きで全テストを実行
    echo   run_tests.bat validate      - テスト環境の検証のみ
    echo.
    echo 詳細なオプションについては以下を実行してください:
    echo   python test_runner.py --help
    goto :end
)

REM 引数に応じてテストを実行
if "%1"=="unit" (
    python test_runner.py --unit --verbose
) else if "%1"=="integration" (
    python test_runner.py --integration --verbose
) else if "%1"=="performance" (
    python test_runner.py --performance --verbose
) else if "%1"=="robustness" (
    python test_runner.py --robustness --verbose
) else if "%1"=="all" (
    python test_runner.py --all --verbose
) else if "%1"=="quick" (
    python test_runner.py --quick --verbose
) else if "%1"=="coverage" (
    python test_runner.py --all --coverage --verbose
) else if "%1"=="validate" (
    python test_runner.py --validate-env
) else (
    echo 不明なオプション: %1
    echo 使用可能なオプション: unit, integration, performance, robustness, all, quick, coverage, validate
)

:end
pause
