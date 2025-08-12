import os
import sys
from pathlib import Path

import uvicorn


if __name__ == "__main__":
    # 現在のディレクトリ構造に合わせてパスを設定
    current_dir = Path(__file__).resolve().parent
    root_dir = current_dir.parents[2]  # WIPディレクトリまで戻る
    src_dir = root_dir / "src"
    
    # PYTHONPATHに追加
    sys.path.insert(0, str(src_dir))
    sys.path.insert(0, str(current_dir))
    
    # 作業ディレクトリを設定
    os.chdir(current_dir)

    # 既定ポートを 80 に変更（環境変数で上書き可能）
    port = int(os.getenv("WEATHER_API_PORT", "80"))
    reload_opt = os.getenv("WEATHER_API_RELOAD", "false").lower() == "true"

    print(f"Starting Weather API Server on port {port}")
    print(f"Working directory: {current_dir}")
    print(f"Python paths added: {src_dir}, {current_dir}")

    uvicorn.run(
        "app:app",  # モジュール名を簡素化
        host="0.0.0.0",
        port=port,
        loop="asyncio",
        reload=reload_opt,
        workers=1,
    )
