# WIP_Server/scripts/update_alert_disaster_data.py の先頭に追加
from ..data import get_alert, get_disaster

def main():
    print("alert処理開始")
    try:
        get_alert.main()
    except Exception as e:
        print(f"Error calling get_alert.main: {e}")
    print("disaster処理開始")
    try:
        get_disaster.main()
    except Exception as e:
        print(f"Error calling get_disaster.main: {e}")
    print("処理完了")

if __name__ == "__main__":
    main()