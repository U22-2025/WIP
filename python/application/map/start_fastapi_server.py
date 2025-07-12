import sys
from pathlib import Path

if __name__ == "__main__":
    # パスを調整してルートからモジュールを参照可能にする
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import uvicorn
    uvicorn.run("map.fastapi_app:app", host="0.0.0.0", port=5000, reload=True)
