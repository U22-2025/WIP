import os
import sys
from pathlib import Path
from common.utils.config_loader import ConfigLoader
import uvicorn

if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent
    os.chdir(base_dir)
    # ルートの python ディレクトリを参照可能にする
    sys.path.insert(0, str(base_dir.parents[1]))
    
    # 設定を読み込む
    config_loader = ConfigLoader()
    workers = config_loader.getint('uvicorn', 'workers', default=1)
    
    uvicorn.run(
        "fastapi_app:app",
        host="0.0.0.0",
        port=5000,
        reload=True,
        workers=workers
    )
