#!/bin/bash
# Weather Data Flow Test Runner
# 
# このスクリプトは天気データフローのテストを実行します
# 
# 使用方法:
#   ./run_flow_tests.sh [simple|full|both]
#
# オプション:
#   simple - 簡単なフローテスト（サーバーが既に起動済みの場合）
#   full   - 完全な統合テスト（テスト用サーバーを自動起動）
#   both   - 両方のテストを実行（デフォルト）

set -e  # エラー時に停止

# カラー出力用
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 設定
TEST_MODE=${1:-both}
REDIS_HOST=${REDIS_HOST:-localhost}
REDIS_PORT=${REDIS_PORT:-6379}
REPORT_SERVER_PORT=${REPORT_SERVER_PORT:-9999}
QUERY_SERVER_PORT=${QUERY_SERVER_PORT:-4111}

echo -e "${BLUE}Weather Data Flow Test Runner${NC}"
echo "================================="
echo "Test Mode: $TEST_MODE"
echo "Redis: $REDIS_HOST:$REDIS_PORT"
echo "Report Server: localhost:$REPORT_SERVER_PORT"
echo "Query Server: localhost:$QUERY_SERVER_PORT"
echo ""

# Redisの起動確認
check_redis() {
    echo -e "${YELLOW}Checking Redis connection...${NC}"
    if redis-cli -h $REDIS_HOST -p $REDIS_PORT ping > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Redis is running${NC}"
    else
        echo -e "${RED}✗ Redis is not running${NC}"
        echo "Please start Redis server:"
        echo "  redis-server"
        exit 1
    fi
}

# Pythonパスの設定
setup_python_path() {
    export PYTHONPATH="/mnt/c/Users/ポッポ焼き/Desktop/WIP/src:$PYTHONPATH"
    echo -e "${YELLOW}Python path configured${NC}"
}

# 簡単なフローテスト（既存サーバー使用）
run_simple_test() {
    echo -e "\n${BLUE}Running Simple Flow Test...${NC}"
    echo "--------------------------------"
    
    # サーバーの起動確認
    echo -e "${YELLOW}Checking if servers are running...${NC}"
    
    # Report Serverの確認
    if nc -z localhost $REPORT_SERVER_PORT 2>/dev/null; then
        echo -e "${GREEN}✓ Report Server is running on port $REPORT_SERVER_PORT${NC}"
    else
        echo -e "${RED}✗ Report Server is not running on port $REPORT_SERVER_PORT${NC}"
        echo "Please start Report Server first"
        return 1
    fi
    
    # Query Serverの確認
    if nc -z localhost $QUERY_SERVER_PORT 2>/dev/null; then
        echo -e "${GREEN}✓ Query Server is running on port $QUERY_SERVER_PORT${NC}"
    else
        echo -e "${RED}✗ Query Server is not running on port $QUERY_SERVER_PORT${NC}"
        echo "Please start Query Server first"
        return 1
    fi
    
    # テスト実行
    python3 tests/simple_flow_test.py \
        --report-port $REPORT_SERVER_PORT \
        --query-port $QUERY_SERVER_PORT \
        --debug
    
    if [ $? -eq 0 ]; then
        echo -e "\n${GREEN}✓ Simple Flow Test PASSED${NC}"
        return 0
    else
        echo -e "\n${RED}✗ Simple Flow Test FAILED${NC}"
        return 1
    fi
}

# 完全な統合テスト（テスト用サーバー自動起動）
run_full_test() {
    echo -e "\n${BLUE}Running Full Integration Test...${NC}"
    echo "-----------------------------------"
    echo -e "${YELLOW}This test will start its own test servers${NC}"
    
    python3 -m pytest tests/test_full_weather_flow.py -v
    
    if [ $? -eq 0 ]; then
        echo -e "\n${GREEN}✓ Full Integration Test PASSED${NC}"
        return 0
    else
        echo -e "\n${RED}✗ Full Integration Test FAILED${NC}"
        return 1
    fi
}

# メイン処理
main() {
    # 前提条件チェック
    check_redis
    setup_python_path
    
    # テストの実行
    case $TEST_MODE in
        "simple")
            run_simple_test
            exit $?
            ;;
        "full")
            run_full_test
            exit $?
            ;;
        "both")
            echo -e "${YELLOW}Running both test modes...${NC}"
            
            simple_result=0
            full_result=0
            
            # 簡単なテスト
            if run_simple_test; then
                simple_result=0
            else
                simple_result=1
            fi
            
            # 完全テスト
            if run_full_test; then
                full_result=0
            else
                full_result=1
            fi
            
            # 結果サマリー
            echo -e "\n${BLUE}Test Results Summary:${NC}"
            echo "===================="
            
            if [ $simple_result -eq 0 ]; then
                echo -e "Simple Test: ${GREEN}PASSED${NC}"
            else
                echo -e "Simple Test: ${RED}FAILED${NC}"
            fi
            
            if [ $full_result -eq 0 ]; then
                echo -e "Full Test: ${GREEN}PASSED${NC}"
            else
                echo -e "Full Test: ${RED}FAILED${NC}"
            fi
            
            total_failed=$((simple_result + full_result))
            if [ $total_failed -eq 0 ]; then
                echo -e "\n${GREEN}🎉 All tests PASSED!${NC}"
                exit 0
            else
                echo -e "\n${RED}💥 $total_failed test(s) FAILED${NC}"
                exit 1
            fi
            ;;
        *)
            echo -e "${RED}Invalid test mode: $TEST_MODE${NC}"
            echo "Valid modes: simple, full, both"
            exit 1
            ;;
    esac
}

# スクリプト実行
main