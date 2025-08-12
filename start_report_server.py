#!/usr/bin/env python3
"""
Report Server Startup Script

レポートサーバーを簡単に起動するスクリプト
"""

import os
import sys
from pathlib import Path

def setup_environment():
    """環境設定"""
    # 現在のディレクトリをWIPルートに設定
    script_dir = Path(__file__).resolve().parent
    os.chdir(script_dir)
    
    # PYTHONPATHにsrcディレクトリを追加
    src_dir = script_dir / "src"
    current_pythonpath = os.environ.get('PYTHONPATH', '')
    if current_pythonpath:
        os.environ['PYTHONPATH'] = f"{src_dir}{os.pathsep}{current_pythonpath}"
    else:
        os.environ['PYTHONPATH'] = str(src_dir)
    
    # sys.pathにも追加
    sys.path.insert(0, str(src_dir))
    
    print(f"Working directory: {script_dir}")
    print(f"Python path: {src_dir}")
    
    # 環境変数設定
    env_vars = {
        'REPORT_SERVER_PORT': '4112',  # Report Serverポート
        'REPORT_SERVER_AUTH_ENABLED': 'false',  # テスト用に認証無効
        'REPORT_SERVER_ENABLE_DATABASE': 'true',  # DB保存有効
        'REDIS_KEY_PREFIX': '',  # 本番用（プレフィックスなし）
        'REPORT_DB_KEY_PREFIX': '',  # 本番用（プレフィックスなし）
    }
    
    for key, value in env_vars.items():
        if key not in os.environ:
            os.environ[key] = value
    
    print("Environment variables configured")

def start_report_server():
    """レポートサーバー起動"""
    try:
        from WIPServerPy.servers.report_server.report_server import ReportServer
        
        print("\nStarting Report Server...")
        print("=" * 40)
        
        # デフォルト設定でサーバー起動
        server = ReportServer(
            host="0.0.0.0",  # 外部からもアクセス可能
            port=4112,       # Report Serverポート
            debug=True,      # デバッグモード有効
            max_workers=4    # ワーカー数
        )
        
        print(f"Report Server starting on 0.0.0.0:4112")
        print("Press Ctrl+C to stop the server")
        print("=" * 40)
        
        # サーバー開始（ブロッキング）
        server.run()
        
    except KeyboardInterrupt:
        print("\n\nReport Server stopped by user")
    except ImportError as e:
        print(f"Import Error: {e}")
        print("\nPlease check:")
        print("1. PYTHONPATH is set correctly")
        print("2. WIPServerPy module is available")
        print("3. All dependencies are installed")
    except Exception as e:
        print(f"Server startup error: {e}")
        import traceback
        traceback.print_exc()

def main():
    """メイン関数"""
    print("Report Server Startup")
    print("=" * 30)
    
    # 環境設定
    setup_environment()
    
    # Redis接続確認
    try:
        import redis
        redis_client = redis.Redis(host='localhost', port=6379, db=0)
        redis_client.ping()
        print("✅ Redis connection confirmed")
    except Exception as e:
        print(f"⚠️ Redis connection failed: {e}")
        print("Please start Redis server:")
        print("  redis-server")
        print()
        response = input("Continue without Redis? (y/N): ")
        if response.lower() != 'y':
            return 1
    
    # サーバー起動
    start_report_server()
    return 0

if __name__ == "__main__":
    sys.exit(main())