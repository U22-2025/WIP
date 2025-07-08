"""
キャッシュでの気温処理のデバッグ用テスト
"""

from common.clients.query_client import QueryClient
import logging

def debug_cache_temperature():
    """キャッシュでの気温処理をデバッグ"""
    
    # ログ設定
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    logger.info("=== キャッシュ気温デバッグテスト ===")
    
    # QueryClientを初期化
    client = QueryClient(debug=True, cache_ttl_minutes=1)
    
    try:
        # テスト用エリアコード
        test_area_code = "130010"  # 東京
        
        # キャッシュクリア
        client.clear_cache()
        
        # 1回目のリクエスト
        logger.info("--- 1回目のリクエスト（サーバーから） ---")
        result1 = client.get_weather_data(
            area_code=test_area_code,
            weather=True,
            temperature=True,
            precipitation_prob=True,
            alert=False,
            disaster=False,
            use_cache=True
        )
        
        if result1 and 'error' not in result1:
            logger.info(f"1回目 - 気温: {result1.get('temperature')}℃")
            logger.info(f"1回目 - レスポンスソース: {result1.get('source', 'server')}")
            
            # キャッシュの中身を直接確認
            cache_key = client._get_cache_key(test_area_code, True, True, True, False, False, 0)
            cached_raw_data = client.cache.get(cache_key)
            if cached_raw_data:
                logger.info(f"キャッシュ内の生データ - 気温: {cached_raw_data.get('temperature')}")
        else:
            logger.error(f"1回目のリクエストが失敗: {result1}")
            return
            
        # 2回目のリクエスト（キャッシュから）
        logger.info("--- 2回目のリクエスト（キャッシュから） ---")
        result2 = client.get_weather_data(
            area_code=test_area_code,
            weather=True,
            temperature=True,
            precipitation_prob=True,
            alert=False,
            disaster=False,
            use_cache=True
        )
        
        if result2 and 'error' not in result2:
            logger.info(f"2回目 - 気温: {result2.get('temperature')}℃")
            logger.info(f"2回目 - レスポンスソース: {result2.get('source', 'server')}")
        else:
            logger.error(f"2回目のリクエストが失敗: {result2}")
            return
            
        # 気温の比較
        temp1 = result1.get('temperature')
        temp2 = result2.get('temperature')
        
        logger.info(f"=== 結果比較 ===")
        logger.info(f"1回目の気温: {temp1}℃")
        logger.info(f"2回目の気温: {temp2}℃")
        logger.info(f"差分: {temp2 - temp1 if temp1 is not None and temp2 is not None else 'N/A'}℃")
        
        if temp1 is not None and temp2 is not None:
            if temp2 == temp1 - 100:
                logger.error("❌ 問題発見: キャッシュから取得した気温が100℃低い")
            elif temp2 == temp1:
                logger.info("✅ 正常: 気温が一致している")
            else:
                logger.warning(f"⚠️  予期しない差分: {temp2 - temp1}℃")
        
    except Exception as e:
        logger.error(f"テスト中にエラーが発生: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        client.close()

if __name__ == "__main__":
    debug_cache_temperature()