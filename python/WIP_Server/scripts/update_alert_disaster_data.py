# WIP_Server/scripts/update_alert_disaster_data.py の先頭に追加
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from WIP_Server.data import get_alert, get_unified_data

def main(redis_prefix='REDIS'):
    print("alert処理開始")
    try:
        get_alert.main(redis_prefix=redis_prefix)
    except Exception as e:
        print(f"Error calling get_alert.main: {e}")
    print("統合災害・地震処理開始")
    try:
        get_unified_data.main(redis_prefix=redis_prefix)
    except Exception as e:
        print(f"Error calling get_unified_data.main: {e}")
    print("処理完了")

if __name__ == "__main__":
    main()
