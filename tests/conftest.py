import sys
from pathlib import Path

# src ディレクトリをインポートパスに追加
ROOT_DIR = Path(__file__).resolve().parents[1]
src_path = ROOT_DIR / 'src'
if src_path.exists():
    sys.path.insert(0, str(src_path))
