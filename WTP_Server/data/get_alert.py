"""
警報・注意報情報取得スクリプト

リファクタリング済みのAlertProcessorを使用して
警報・注意報情報を取得・処理します。

使用方法:
    python get_alert.py
"""

from alert_processor import AlertProcessor


def main():
    """
    警報・注意報処理のメイン関数
    
    AlertProcessorを使用して警報・注意報情報を取得し、
    JSON形式で出力します。
    """
    print("=== 警報・注意報情報取得開始 ===")
    
    # AlertProcessorのインスタンスを作成
    processor = AlertProcessor()
    
    # 全ての警報・注意報情報を処理
    json_result = processor.process_all_alerts('wtp/json/alert_data.json')
    
    print("=== 警報・注意報情報取得完了 ===")
    print(json_result)


if __name__ == "__main__":
    main()
