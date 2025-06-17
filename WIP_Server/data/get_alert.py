"""
警報・注意報情報取得スクリプト

リファクタリング済みのAlertProcessorを使用して
警報・注意報情報を取得・処理し、Redisに格納します。

使用方法:
    python get_alert.py
"""

from alert_processor import AlertDataProcessor
from redis_manager import create_redis_manager


def main():
    """
    警報・注意報処理のメイン関数
    
    AlertProcessorを使用して警報・注意報情報を取得し、
    既存のRedis気象データに追加します。
    """
    print("=== 警報・注意報情報取得開始 ===")
    
    # AlertDataProcessorのインスタンスを作成
    processor = AlertDataProcessor()
    
    # Step 1: XMLファイルリストの取得
    print("Step 1: Getting XML file list...")
    url_list = processor.get_alert_xml_list()
    print(f"Found {len(url_list)} URLs")
    if not url_list:
        print("No URLs found. Exiting.")
        return
    
    # Step 2: 警報・注意報情報の取得・統合
    print("Step 2: Processing alert info...")
    json_result = processor.get_alert_info(url_list, 'wip/json/alert_data.json')
    
    print("=== 警報・注意報情報取得完了 ===")
    import json
    print(json.dumps(json_result, ensure_ascii=False, indent=2))
    
    # Redis管理クラスを使用してデータを更新
    print("\n=== Redisデータ更新開始 ===")
    
    try:
        # Redis管理クラスのインスタンスを作成
        redis_manager = create_redis_manager(debug=True)
        
        # 警報・注意報情報を更新
        # RedisManagerのupdate_alertsはarea_alert_mapping部分を期待
        result = redis_manager.update_alerts(json_result["area_alert_mapping"])
        
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


if __name__ == "__main__":
    main()
