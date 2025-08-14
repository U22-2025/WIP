#!/usr/bin/env python3
"""
Weather API Server Direct Runner

FastAPIサーバーを直接実行するスクリプト。
モジュールの問題を回避して確実にサーバーを起動します。
"""

import os
import sys
from pathlib import Path

# パスの設定
current_dir = Path(__file__).resolve().parent
root_dir = current_dir.parents[2]  # WIPディレクトリ
src_dir = root_dir / "src"

# PYTHONPATHに追加
sys.path.insert(0, str(src_dir))
sys.path.insert(0, str(current_dir))

# 作業ディレクトリを設定
os.chdir(current_dir)

try:
    import uvicorn
    from app import app
    
    print("Weather API Server - Direct Runner")
    print("=" * 40)
    print(f"Working directory: {current_dir}")
    print(f"Source path: {src_dir}")
    
    # 環境変数設定
    port = int(os.getenv("WEATHER_API_PORT", "8001"))
    host = os.getenv("WEATHER_API_HOST", "0.0.0.0")
    reload_opt = os.getenv("WEATHER_API_RELOAD", "false").lower() == "true"
    
    print(f"Server will start on {host}:{port}")
    print(f"Reload mode: {reload_opt}")
    print("=" * 40)
    
    # サーバー起動
    uvicorn.run(
        app,  # appオブジェクトを直接渡す
        host=host,
        port=port,
        reload=reload_opt,
        workers=1,
        log_level="info"
    )
    
except ImportError as e:
    print(f"Import Error: {e}")
    print("Required packages might be missing:")
    print("  pip install fastapi uvicorn requests")
    sys.exit(1)
except Exception as e:
    print(f"Server startup failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)