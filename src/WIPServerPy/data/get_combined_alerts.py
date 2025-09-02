"""
統合警報・注意報情報取得スクリプト

従来の警報・注意報処理（extra.xml）と新しい海上警報・注意報処理（other.xml）を
統合して実行し、Redisに格納します。

使用方法:
    python get_combined_alerts.py
"""

import sys
import os
from pathlib import Path

# パスを追加して直接実行にも対応
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from WIPServerPy.data.alert_processor import AlertDataProcessor, AlertProcessor
from WIPServerPy.data.maritime_alert_processor import MaritimeAlertProcessor
from WIPServerPy.data.redis_manager import create_redis_manager


def main():
    """
    統合警報・注意報処理のメイン関数

    従来の警報・注意報と海上警報・注意報の両方を処理し、
    既存のRedis気象データに追加します。
    """
    print("=== 統合警報・注意報情報取得開始 ===")

    # プロセッサのインスタンスを作成
    alert_processor = AlertDataProcessor()
    alert_lister = AlertProcessor()
    maritime_processor = MaritimeAlertProcessor()
    
    try:
        # Redis管理クラスのインスタンスを作成（最初に作成して使い回し）
        redis_manager = create_redis_manager(debug=True)

        # ===== 従来の警報・注意報処理 =====
        print("\n=== Step 1: 従来の警報・注意報処理（extra.xml）===")
        
        try:
            # Step 1-1: XMLファイルリストの取得
            print("Step 1-1: Getting traditional alert XML list...")
            alert_url_list = alert_lister.get_alert_xml_list()

            print(f"Found {len(alert_url_list)} traditional alert URLs")
            if alert_url_list:
                # Step 1-2: 警報・注意報情報の取得・統合
                print("Step 1-2: Processing traditional alert info...")
                alert_result = alert_processor.get_alert_info(alert_url_list)

                # Redis更新
                if alert_result and len(alert_result) > 1:  # タイムスタンプ以外にデータがある場合
                    result = redis_manager.update_alerts(alert_result)
                    print(f"従来警報更新結果: 更新={result['updated']}, 新規={result['created']}, エラー={result['errors']}")
                else:
                    print("従来の警報・注意報データが見つかりませんでした")
            else:
                print("従来の警報・注意報URLが見つかりませんでした")

        except Exception as e:
            print(f"従来の警報・注意報処理でエラー: {e}")

        # ===== 海上警報・注意報処理 =====
        print("\n=== Step 2: 海上警報・注意報処理（other.xml）===")
        
        try:
            # Step 2-1: 海上警報・注意報情報の取得・統合
            print("Step 2-1: Getting maritime alert info...")
            maritime_result = maritime_processor.get_maritime_alerts()

            print(f"Processed {len([k for k in maritime_result.keys() if k != 'alert_pulldatetime'])} maritime areas")
            
            # Redis更新（海上警報を通常の警報フィールドに統合）
            if maritime_result and len(maritime_result) > 1:  # タイムスタンプ以外にデータがある場合
                result = redis_manager.update_alerts(maritime_result)
                print(f"海上警報更新結果: 更新={result['updated']}, 新規={result['created']}, エラー={result['errors']}")
            else:
                print("海上警報・注意報データが見つかりませんでした")

        except Exception as e:
            print(f"海上警報・注意報処理でエラー: {e}")

        # 接続を閉じる
        redis_manager.close()
        print("\n=== 統合警報・注意報情報取得完了 ===")

    except Exception as e:
        print(f"Error in combined alert processing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()