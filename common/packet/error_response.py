from .response import Response
from .extended_field import ExtendedField

class ErrorResponse(Response):
    def __init__(self):
        super().__init__()
        self.version = 1
        self.type = 7  # エラーパケットタイプ
        self.weather_code = 0  # エラーコード格納用
        self.ex_field = ExtendedField()  # ソースIP格納用
        
    @property
    def error_code(self):
        return self.weather_code
        
    @error_code.setter
    def error_code(self, value):
        self.weather_code = value
        
    def serialize(self):
        # 基本フィールドをシリアライズ
        base_data = super().to_bytes()
        # ex_fieldをシリアライズして追加
        ex_data = self.ex_field.serialize()
        return base_data + ex_data
        
    def deserialize(self, data):
        # 基本フィールドをデシリアライズ
        base_len = super().deserialize(data)
        # ex_fieldをデシリアライズ
        ex_data = data[base_len:]
        self.ex_field.deserialize(ex_data)
        return base_len + len(ex_data)