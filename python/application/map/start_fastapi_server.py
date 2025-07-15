import os
import sys
from pathlib import Path
import uvicorn
if __name__ == "__main__":
    sys.path.insert(
        0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )

from common.utils.config_loader import ConfigLoader

if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent
    os.chdir(base_dir)
    # ルートの python ディレクトリを参照可能にする
    sys.path.insert(0, str(base_dir.parents[1]))
    
    # 設定を読み込む
    config_loader = ConfigLoader()
    workers = config_loader.getint('uvicorn', 'workers', default=1)
    reload_opt = config_loader.getboolean('uvicorn', 'reload', default=False)

    if workers > 1 and reload_opt:
        print("Warning: workers が 1 より大きい場合は reload を無効化します")
        reload_opt = False

    if sys.platform.startswith("win") and workers > 1:
        print("Warning: Windows環境ではworkers>1はサポートされていません。workers=1に変更します")
        workers = 1

    uvicorn.run(
        "fastapi_app:app",
        host="0.0.0.0",
        port=5000,
        loop="asyncio",
        reload=reload_opt,
        workers=workers
    )
