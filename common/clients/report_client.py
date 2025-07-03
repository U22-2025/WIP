"""
Report Client - IoT機器データ収集専用クライアント（エントリポイント）
common/packet/report_client.pyのReportClientを使用してレポート機能を提供
"""

import logging
import time
import os
from ..packet.report_client import ReportClient


def main():
    """メイン関数 - 使用例"""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.info("Report Client Example - IoT Sensor Data Reporting")
    logger.info("=" * 60)
    
    # 環境変数またはデフォルト値でサーバー情報を設定（weather_server経由）
    host = os.getenv('WEATHER_SERVER_HOST', 'localhost')
    port = int(os.getenv('WEATHER_SERVER_PORT', '4110'))
    
    client = ReportClient(host=host, port=port, debug=True)
    
    try:
        # 例1: センサーデータを個別に設定
        logger.info("\n1. Setting sensor data individually")
        logger.info("-" * 40)
        
        client.set_area_code("011000")  # 札幌
        client.set_weather_code(100)    # 晴れ
        client.set_temperature(25.5)    # 25.5℃
        client.set_precipitation_prob(30)  # 30%
        
        # 現在のデータを確認
        current_data = client.get_current_data()
        logger.info(f"Current data: {current_data}")
        
        # レポート送信
        result = client.send_report()
        if result:
            logger.info("\n✓ Report sent successfully!")
            logger.info(f"Response: {result}")
        else:
            logger.error("\n✗ Failed to send report")
        
        # 例2: データを一括設定して送信
        logger.info("\n\n2. Setting sensor data in batch")
        logger.info("-" * 40)
        
        client.set_sensor_data(
            area_code="130000",  # 東京
            weather_code=200,    # 曇り
            temperature=22.3,    # 22.3℃
            precipitation_prob=60,  # 60%
            alert=["大雨注意報"],
        )
        
        result = client.send_current_data()
        if result:
            logger.info("\n✓ Batch report sent successfully!")
            logger.info(f"Response: {result}")
        else:
            logger.error("\n✗ Failed to send batch report")
            
        # 例3: 警報・災害情報付きレポート
        logger.info("\n\n3. Sending report with alert and disaster info")
        logger.info("-" * 50)
        
        client.clear_data()
        client.set_sensor_data(
            area_code="270000",  # 大阪
            weather_code=300,    # 雨
            temperature=18.7,    # 18.7℃
            precipitation_prob=80,  # 80%
            alert=["大雨警報", "洪水注意報"],
            disaster=["河川氾濫危険情報"]
        )
        
        result = client.send_report()
        if result:
            logger.info("\n✓ Alert report sent successfully!")
            logger.info(f"Response: {result}")
        else:
            logger.error("\n✗ Failed to send alert report")
            
    finally:
        client.close()
        
    logger.info("\n" + "="*60)
    logger.info("Report Client Example completed")
    logger.info("✓ IoT sensor data reporting functionality demonstrated")


def create_report_client(host='localhost', port=4110, debug=False):
    """
    ReportClientインスタンスを作成する便利関数
    
    Args:
        host: 天気サーバーのホスト（レポートを転送）
        port: 天気サーバーのポート
        debug: デバッグモード
        
    Returns:
        ReportClient: 設定されたReportClientインスタンス
    """
    return ReportClient(host=host, port=port, debug=debug)


def send_sensor_report(area_code, weather_code=None, temperature=None,
                      precipitation_prob=None, alert=None, disaster=None,
                      host='localhost', port=4110, debug=False):
    """
    センサーレポートを一回の呼び出しで送信する便利関数
    
    Args:
        area_code: エリアコード
        weather_code: 天気コード
        temperature: 気温（摂氏）
        precipitation_prob: 降水確率（0-100%）
        alert: 警報情報
        disaster: 災害情報
        host: 天気サーバーのホスト（レポートを転送）
        port: 天気サーバーのポート
        debug: デバッグモード
        
    Returns:
        dict: レスポンス情報、またはNone（エラー時）
    """
    client = ReportClient(host=host, port=port, debug=debug)
    
    try:
        client.set_sensor_data(
            area_code=area_code,
            weather_code=weather_code,
            temperature=temperature,
            precipitation_prob=precipitation_prob,
            alert=alert,
            disaster=disaster
        )
        
        return client.send_report()
        
    finally:
        client.close()


if __name__ == "__main__":
    main()
