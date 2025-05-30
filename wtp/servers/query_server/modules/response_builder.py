"""
レスポンス作成クラス
気象データからレスポンスパケットを構築
"""

import time
from .weather_constants import WeatherConstants

try:
    # モジュールとして使用される場合
    from ..packet import Response
except ImportError:
    # 直接実行される場合のフォールバック
    try:
        from wtp.packet import Response
    except ImportError:
        from packet import Response


class ResponseBuilder:
    """レスポンス作成クラス"""
    
    def __init__(self, config_manager):
        """
        初期化
        
        Args:
            config_manager: 設定管理オブジェクト
        """
        self.config = config_manager
        self.debug = config_manager.debug
        self.version = config_manager.version
    
    def _extract_weather_code(self, weather_data):
        """
        天気コードを抽出・変換
        
        Args:
            weather_data: 気象データ
            
        Returns:
            int: 天気コード
        """
        if 'weather' not in weather_data or not weather_data['weather']:
            return WeatherConstants.DEFAULT_WEATHER_CODE
        
        try:
            weather_code = int(weather_data['weather']) if weather_data['weather'] else 0
            return weather_code
        except (ValueError, TypeError):
            return WeatherConstants.DEFAULT_WEATHER_CODE
    
    def _extract_temperature(self, weather_data):
        """
        気温を抽出・変換
        
        Args:
            weather_data: 気象データ
            
        Returns:
            int: 変換された気温値（0-255）
        """
        if 'temperature' not in weather_data or not weather_data['temperature']:
            return WeatherConstants.DEFAULT_TEMPERATURE
        
        try:
            temp_str = weather_data['temperature']
            if not temp_str or temp_str == "":
                return WeatherConstants.DEFAULT_TEMPERATURE
            
            # 気温を数値に変換
            temp_val = int(float(temp_str))
            
            # -100℃～+155℃を0-255で表現
            temperature = temp_val + WeatherConstants.TEMPERATURE_OFFSET
            
            # 範囲制限
            return max(WeatherConstants.MIN_TEMPERATURE, 
                      min(WeatherConstants.MAX_TEMPERATURE, temperature))
            
        except (ValueError, TypeError):
            return WeatherConstants.DEFAULT_TEMPERATURE
    
    def _extract_precipitation(self, weather_data):
        """
        降水確率を抽出・変換
        
        Args:
            weather_data: 気象データ
            
        Returns:
            int: 降水確率（0-100）
        """
        if 'precipitation' not in weather_data or not weather_data['precipitation']:
            return WeatherConstants.DEFAULT_PRECIPITATION
        
        try:
            pops_str = weather_data['precipitation']
            if not pops_str or pops_str == "":
                return WeatherConstants.DEFAULT_PRECIPITATION
            
            pops = int(pops_str)
            
            # 0-100%の範囲制限
            return max(WeatherConstants.MIN_PRECIPITATION, 
                      min(WeatherConstants.MAX_PRECIPITATION, pops))
            
        except (ValueError, TypeError):
            return WeatherConstants.DEFAULT_PRECIPITATION
    
    def _build_extended_field(self, weather_data):
        """
        拡張フィールドを構築
        
        Args:
            weather_data: 気象データ
            
        Returns:
            dict: 拡張フィールドデータ
        """
        ex_field = {}
        
        if 'warnings' in weather_data and weather_data['warnings']:
            ex_field['alert'] = weather_data['warnings']
            
        if 'disaster_info' in weather_data and weather_data['disaster_info']:
            ex_field['disaster'] = weather_data['disaster_info']
        
        return ex_field
    
    def _build_base_response_params(self, request, area_code):
        """
        基本レスポンスパラメータを構築
        
        Args:
            request: リクエストパケット
            area_code: エリアコード
            
        Returns:
            dict: 基本レスポンスパラメータ
        """
        return {
            'version': self.version,
            'packet_id': request.packet_id,
            'type': WeatherConstants.RESPONSE_TYPE,
            'ex_flag': WeatherConstants.EX_FIELD_DISABLED,
            'timestamp': int(time.time()),
            'area_code': area_code
        }
    
    def _add_weather_data_to_response(self, response_params, weather_data):
        """
        気象データをレスポンスパラメータに追加
        
        Args:
            response_params: レスポンスパラメータ
            weather_data: 気象データ
        """
        if not weather_data:
            return
        
        # 固定長フィールドのデータを追加
        response_params.update({
            'weather_code': self._extract_weather_code(weather_data),
            'temperature': self._extract_temperature(weather_data),
            'pops': self._extract_precipitation(weather_data)
        })
        
        # 拡張フィールドの処理
        ex_field = self._build_extended_field(weather_data)
        if ex_field:
            response_params['ex_flag'] = WeatherConstants.EX_FIELD_ENABLED
            response_params['ex_field'] = ex_field
    
    def create_response(self, request, area_code, weather_data):
        """
        リクエストと気象データからレスポンスを作成
        
        Args:
            request: リクエストパケット
            area_code: エリアコード
            weather_data: 気象データ
            
        Returns:
            bytes: レスポンスパケットのバイト列
        """
        try:
            # 基本レスポンスパラメータを構築
            response_params = self._build_base_response_params(request, area_code)
            
            # 気象データを追加
            self._add_weather_data_to_response(response_params, weather_data)
            
            # レスポンスオブジェクトを作成してバイト列に変換
            response = Response(**response_params)
            return response.to_bytes()
            
        except Exception as e:
            if self.debug:
                print(f"Error creating response: {e}")
            
            # エラー時は最小限のレスポンスを作成
            fallback_params = self._build_base_response_params(request, area_code)
            response = Response(**fallback_params)
            return response.to_bytes()
    
    def validate_request(self, request):
        """
        リクエストの妥当性をチェック
        
        Args:
            request: リクエストパケット
            
        Returns:
            tuple: (is_valid, error_message)
        """
        # リクエストタイプのチェック
        if request.type != WeatherConstants.REQUEST_TYPE:
            return False, f"Invalid request type: {request.type}, expected {WeatherConstants.REQUEST_TYPE}"
        
        # エリアコードのチェック
        if not request.area_code:
            return False, "No area code in request"
        
        return True, None
