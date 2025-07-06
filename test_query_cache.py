"""
QueryClientのキャッシュ機能テスト
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from common.clients.query_client import QueryClient
import time
import logging

def test_query_cache():
    """QueryClientのキャッシュ機能をテスト"""
    
    # ログ設定
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    logger.info("QueryClient キャッシュ機能テスト開始")
    logger.info("=" * 60)
    
    # テスト用エリアコード
    test_area_code = "130010"  # 東京
    
    # QueryClientを初期化（キャッシュTTL=1分でテスト）
    client = QueryClient(debug=True, cache_ttl_minutes=1)
    
    try:
        logger.info("初期キャッシュ統計:")
        stats = client.get_cache_stats()
        logger.info(f"キャッシュサイズ: {stats['cache_size']}")
        logger.info(f"キャッシュTTL: {stats['cache_ttl_minutes']}分")
        
        # 1回目のリクエスト - キャッシュミスが発生するはず
        logger.info(f"\n--- 1回目のリクエスト（{test_area_code}） ---")
        start_time = time.time()
        result1 = client.get_weather_data(
            area_code=test_area_code,
            weather=True,
            temperature=True,
            precipitation_prob=True,
            alert=False,
            disaster=False,
            use_cache=True
        )
        end_time = time.time()
        
        if result1 and 'error' not in result1:
            logger.info(f"1回目 - エリアコード: {result1.get('area_code')}")
            logger.info(f"1回目 - 処理時間: {result1.get('timing', {}).get('total_time', 0):.2f}ms")
            logger.info(f"1回目 - 実測時間: {(end_time-start_time)*1000:.2f}ms")
            logger.info(f"1回目 - 天気コード: {result1.get('weather_code')}")
            logger.info(f"1回目 - 気温: {result1.get('temperature')}℃")
        else:
            logger.error("1回目のリクエストが失敗しました")
            logger.error(f"エラー内容: {result1}")
            
        # キャッシュ統計確認
        stats = client.get_cache_stats()
        logger.info(f"\n1回目後のキャッシュサイズ: {stats['cache_size']}")
        
        # 2回目のリクエスト - キャッシュヒットが発生するはず
        logger.info(f"\n--- 2回目のリクエスト（同じ条件） ---")
        start_time = time.time()
        result2 = client.get_weather_data(
            area_code=test_area_code,
            weather=True,
            temperature=True,
            precipitation_prob=True,
            alert=False,
            disaster=False,
            use_cache=True
        )
        end_time = time.time()
        
        if result2 and 'error' not in result2:
            logger.info(f"2回目 - エリアコード: {result2.get('area_code')}")
            logger.info(f"2回目 - 処理時間: {result2.get('timing', {}).get('total_time', 0):.2f}ms")
            logger.info(f"2回目 - 実測時間: {(end_time-start_time)*1000:.2f}ms")
            logger.info(f"2回目 - レスポンスソース: {result2.get('source', 'server')}")
            logger.info(f"2回目 - 天気コード: {result2.get('weather_code')}")
            logger.info(f"2回目 - 気温: {result2.get('temperature')}℃")
        else:
            logger.error("2回目のリクエストが失敗しました")
            logger.error(f"エラー内容: {result2}")
        
        # 処理時間比較
        if (result1 and result2 and 'error' not in result1 and 'error' not in result2):
            time1 = result1.get('timing', {}).get('total_time', 0)
            time2 = result2.get('timing', {}).get('total_time', 0)
            if time1 > 0 and time2 >= 0:
                if time2 < time1:
                    speed_up = (time1 - time2) / time1 * 100
                    logger.info(f"\nキャッシュによる高速化: {speed_up:.1f}%")
                else:
                    logger.info(f"\n処理時間比較: 1回目={time1:.2f}ms, 2回目={time2:.2f}ms")
        
        # 異なる条件でのテスト（アラート付き）
        logger.info(f"\n--- 異なる条件でのリクエスト（アラート付き） ---")
        result3 = client.get_weather_data(
            area_code=test_area_code,
            weather=True,
            temperature=True,
            precipitation_prob=True,
            alert=True,  # アラートフラグを追加
            disaster=False,
            use_cache=True
        )
        
        if result3 and 'error' not in result3:
            logger.info(f"異なる条件 - エリアコード: {result3.get('area_code')}")
            logger.info(f"異なる条件 - 処理時間: {result3.get('timing', {}).get('total_time', 0):.2f}ms")
            logger.info(f"異なる条件 - レスポンスソース: {result3.get('source', 'server')}")
        else:
            logger.error("異なる条件のリクエストが失敗しました")
            logger.error(f"エラー内容: {result3}")
            
        # 最終キャッシュ統計
        stats = client.get_cache_stats()
        logger.info(f"\n最終キャッシュサイズ: {stats['cache_size']}")
        
        # 簡便メソッドのテスト
        logger.info(f"\n--- 簡便メソッドのテスト ---")
        simple_result = client.get_weather_simple(
            area_code=test_area_code,
            include_all=False,
            use_cache=True
        )
        
        if simple_result and 'error' not in simple_result:
            logger.info(f"簡便メソッド - エリアコード: {simple_result.get('area_code')}")
            logger.info(f"簡便メソッド - レスポンスソース: {simple_result.get('source', 'server')}")
        else:
            logger.error("簡便メソッドが失敗しました")
            logger.error(f"エラー内容: {simple_result}")
        
        # キャッシュクリアのテスト
        logger.info(f"\n--- キャッシュクリアのテスト ---")
        client.clear_cache()
        stats = client.get_cache_stats()
        logger.info(f"クリア後のキャッシュサイズ: {stats['cache_size']}")
        
        logger.info("\n" + "=" * 60)
        logger.info("QueryClient キャッシュ機能テスト完了")
        
    except Exception as e:
        logger.error(f"テスト中にエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        client.close()

if __name__ == "__main__":
    test_query_cache()
