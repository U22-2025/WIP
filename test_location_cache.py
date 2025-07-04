"""
LocationClientのキャッシュ機能テスト
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from common.clients.location_client import LocationClient
import time
import logging

def test_location_cache():
    """LocationClientのキャッシュ機能をテスト"""
    
    # ログ設定
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    logger.info("LocationClient キャッシュ機能テスト開始")
    logger.info("=" * 60)
    
    # 東京の座標
    tokyo_lat = 35.6895
    tokyo_lon = 139.6917
    
    # 大阪の座標
    osaka_lat = 34.6937
    osaka_lon = 135.5023
    
    # LocationClientを初期化（キャッシュTTL=1分でテスト）
    client = LocationClient(debug=True, cache_ttl_minutes=1)
    
    try:
        logger.info("初期キャッシュ統計:")
        stats = client.get_cache_stats()
        logger.info(f"キャッシュサイズ: {stats['cache_size']}")
        logger.info(f"キャッシュTTL: {stats['cache_ttl_minutes']}分")
        
        # 1回目のリクエスト - キャッシュミスが発生するはず
        logger.info("\n--- 1回目のリクエスト（東京） ---")
        start_time = time.time()
        response1, process_time1 = client.get_location_data(tokyo_lat, tokyo_lon)
        end_time = time.time()
        
        if response1 and response1.is_valid():
            logger.info(f"1回目 - エリアコード: {response1.get_area_code()}")
            logger.info(f"1回目 - 処理時間: {process_time1*1000:.2f}ms")
            logger.info(f"1回目 - 実測時間: {(end_time-start_time)*1000:.2f}ms")
        else:
            logger.error("1回目のリクエストが失敗しました")
            
        # キャッシュ統計確認
        stats = client.get_cache_stats()
        logger.info(f"\n1回目後のキャッシュサイズ: {stats['cache_size']}")
        
        # 2回目のリクエスト - キャッシュヒットが発生するはず
        logger.info("\n--- 2回目のリクエスト（同じ座標） ---")
        start_time = time.time()
        response2, process_time2 = client.get_location_data(tokyo_lat, tokyo_lon)
        end_time = time.time()
        
        if response2 and response2.is_valid():
            logger.info(f"2回目 - エリアコード: {response2.get_area_code()}")
            logger.info(f"2回目 - 処理時間: {process_time2*1000:.2f}ms")
            logger.info(f"2回目 - 実測時間: {(end_time-start_time)*1000:.2f}ms")
            logger.info(f"2回目 - レスポンスソース: {response2.get_source_info()}")
        else:
            logger.error("2回目のリクエストが失敗しました")
        
        # 処理時間比較
        if process_time1 > 0 and process_time2 > 0:
            speed_up = (process_time1 - process_time2) / process_time1 * 100
            logger.info(f"\nキャッシュによる高速化: {speed_up:.1f}%")
        
        # 異なる座標でのテスト
        logger.info("\n--- 異なる座標でのリクエスト（大阪） ---")
        response3, process_time3 = client.get_location_data(osaka_lat, osaka_lon)
        
        if response3 and response3.is_valid():
            logger.info(f"大阪 - エリアコード: {response3.get_area_code()}")
            logger.info(f"大阪 - 処理時間: {process_time3*1000:.2f}ms")
        else:
            logger.error("大阪のリクエストが失敗しました")
            
        # 最終キャッシュ統計
        stats = client.get_cache_stats()
        logger.info(f"\n最終キャッシュサイズ: {stats['cache_size']}")
        
        # 簡便メソッドのテスト
        logger.info("\n--- 簡便メソッドのテスト ---")
        area_code = client.get_area_code_simple(tokyo_lat, tokyo_lon)
        logger.info(f"簡便メソッド - エリアコード: {area_code}")
        
        # キャッシュクリアのテスト
        logger.info("\n--- キャッシュクリアのテスト ---")
        client.clear_cache()
        stats = client.get_cache_stats()
        logger.info(f"クリア後のキャッシュサイズ: {stats['cache_size']}")
        
        logger.info("\n" + "=" * 60)
        logger.info("LocationClient キャッシュ機能テスト完了")
        
    except Exception as e:
        logger.error(f"テスト中にエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        client.close()

if __name__ == "__main__":
    test_location_cache()