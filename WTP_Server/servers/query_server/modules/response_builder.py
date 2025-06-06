"""
レスポンス構築クラス
リクエストに基づいてレスポンスパケットを構築
"""

import time
import sys
import os
# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))

from common.packet import Response


class ResponseBuilder:
    """レスポンスビルダー"""
    
    def __init__(self, config):
        """
        初期化
        
        Args:
            config: 設定辞書（debug, version）
        """
        self.debug = config.get('debug', False)
        self.version = config.get('version', 1)
    
    def build_response(self, request, weather_data):
        """
        レスポンスを構築
        
        Args:
            request: リクエストオブジェクト
            weather_data: 気象データ辞書
            
        Returns:
            Response: レスポンスオブジェクト
        """
        # 基本レスポンスを作成
        response = Response(
            version=self.version,
            packet_id=request.packet_id,
            type=3,  # Type 3 for weather data response
            area_code=request.area_code,
            day=request.day,
            timestamp=int(time.time()),
            weather_flag=request.weather_flag,
            temperature_flag=request.temperature_flag,
            pops_flag=request.pops_flag,
            alert_flag=request.alert_flag,
            disaster_flag=request.disaster_flag,
            ex_flag=0  # デフォルトは0
        )
        
        # 気象データを設定
        if weather_data:
            self._set_weather_data(response, request, weather_data)
        
        # 拡張フィールドを設定
        if request.ex_flag or request.alert_flag or request.disaster_flag:
            self._set_extended_fields(response, request, weather_data)
        
        return response
    
    def _set_weather_data(self, response, request, weather_data):
        """基本気象データを設定"""
        if request.weather_flag and 'weather' in weather_data:
            weather_value = weather_data['weather']
            # リストの場合は最初の要素を使用
            if isinstance(weather_value, list):
                response.weather_code = int(weather_value[0]) if weather_value else 0
            else:
                response.weather_code = int(weather_value) if weather_value else 0
        
        if request.temperature_flag and 'temperature' in weather_data:
            temp_data = weather_data['temperature']
            # リストの場合は最初の要素を使用
            if isinstance(temp_data, list):
                actual_temp = int(temp_data[0]) if temp_data else 25
            else:
                actual_temp = int(temp_data) if temp_data else 25
            # パケットフォーマットに合わせて変換（実際の温度 + 100）
            response.temperature = actual_temp + 100
        
        if request.pops_flag and 'precipitation_prob' in weather_data:
            pops_value = weather_data['precipitation_prob']
            # リストの場合は最初の要素を使用
            if isinstance(pops_value, list):
                response.pops = int(pops_value[0]) if pops_value else 0
            else:
                response.pops = int(pops_value) if pops_value else 0
    
    def _set_extended_fields(self, response, request, weather_data):
        """拡張フィールドを設定"""
        response.ex_flag = 1
        
        # sourceを引き継ぐ
        if hasattr(request, 'ex_field') and request.ex_field:
            source = request.ex_field.get('source')
            if source:
                response.ex_field.set('source', source)
        
        # 警報情報
        if request.alert_flag and weather_data and 'warnings' in weather_data:
            response.ex_field.set('alert', weather_data['warnings'])
        
        # 災害情報
        if request.disaster_flag and weather_data and 'disaster_info' in weather_data:
            response.ex_field.set('disaster', weather_data['disaster_info'])
    
    def build_error_response(self, request, error_code, error_message):
        """
        エラーレスポンスを構築
        
        Args:
            request: リクエストオブジェクト
            error_code: エラーコード
            error_message: エラーメッセージ
            
        Returns:
            Response: エラーレスポンスオブジェクト
        """
        response = Response(
            version=self.version,
            packet_id=request.packet_id,
            type=3,
            area_code=request.area_code,
            day=request.day,
            timestamp=int(time.time()),
            weather_flag=0,
            temperature_flag=0,
            pops_flag=0,
            alert_flag=0,
            disaster_flag=0,
            ex_flag=1
        )
        
        # エラー情報を拡張フィールドに設定
        # ExtendedFieldオブジェクトはResponseのコンストラクタで作成されるため、
        # 辞書形式でデータを設定することはできません
        # 代わりに、個別にsetメソッドを使用する必要があります
        # ただし、エラー情報は標準の拡張フィールドではないため、
        # 別の方法で処理する必要があります
        
        # sourceを引き継ぐ
        if hasattr(request, 'ex_field') and request.ex_field:
            source = request.ex_field.get('source')
            if source:
                response.ex_field.set('source', source)
        
        return response
