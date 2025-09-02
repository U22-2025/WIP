"""
海上警報・注意報情報取得スクリプト

MaritimeAlertProcessorを使用して海上警報・注意報情報を取得・処理し、Redisに格納します。

使用方法:
    python get_maritime_alert.py
"""

import sys
import os
from pathlib import Path

# パスを追加して直接実行にも対応
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from WIPServerPy.data.maritime_alert_processor import MaritimeAlertProcessor
from WIPServerPy.data.redis_manager import create_redis_manager


def main():
    """
    海上警報・注意報処理のメイン関数

    MaritimeAlertProcessorを使用して海上警報・注意報情報を取得し、
    既存のRedis気象データに追加します。
    """
    print("=== 海上警報・注意報情報取得開始 ===")

    # MaritimeAlertProcessorのインスタンスを作成
    processor = MaritimeAlertProcessor()
    
    try:
        # Step 1: 海上警報・注意報情報の取得・統合
        print("Step 1: Getting maritime alert info...")
        json_result = processor.get_maritime_alerts()

        print(f"Processed {len([k for k in json_result.keys() if k != 'alert_pulldatetime'])} areas")
        
        if not json_result or len(json_result) <= 1:  # 1はタイムスタンプのみの場合
            print("No maritime alert data found. Exiting.")
            return

        print("\n=== 海上警報・注意報情報取得完了 ===")

        # Redis管理クラスを使用してデータを更新
        print("\n=== Redisデータ更新開始 ===")

        try:
            # Redis管理クラスのインスタンスを作成
            redis_manager = create_redis_manager(debug=True)

            # 海上警報・注意報情報を更新（通常の警報フィールドに統合）
            result = redis_manager.update_alerts(json_result)

            # 結果を表示
            print(f"\n=== Redis更新結果 ===")
            print(f"更新されたエリア: {result['updated']}件")
            print(f"新規作成されたエリア: {result['created']}件")
            print(f"エラー: {result['errors']}件")
            print(f"合計処理エリア: {result['updated'] + result['created']}件")

            # 接続を閉じる
            redis_manager.close()

            print("=== Redisデータ更新完了 ===")

        except Exception as e:
            print(f"Redis更新エラー: {e}")
            
    except Exception as e:
        print(f"Error in maritime alert processing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()