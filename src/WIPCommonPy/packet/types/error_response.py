from WIPCommonPy.packet.models.response import Response
from WIPCommonPy.packet.core.extended_field import ExtendedField
from typing import Optional, Union, Dict, Any


class ErrorResponse(Response):
    """Type7 Error packet with optional source information."""

    def __init__(
        self,
        *,
        version: int = 1,
        packet_id: int = 0,
        error_code: Union[int, str] = 0,
        timestamp: Optional[int] = None,
        ex_field: Optional[Union[Dict[str, Any], ExtendedField]] = None,
        **kwargs,
    ) -> None:
        # 呼び出し元から type や ex_flag が渡された場合は取り除く
        type_val = kwargs.pop("type", 7)
        ex_flag_val = kwargs.pop("ex_flag", 1)

        super().__init__(
            version=version,
            packet_id=packet_id,
            type=type_val,
            ex_flag=ex_flag_val,
            timestamp=timestamp or 0,
            weather_code=int(error_code),
            ex_field=ex_field,
            **kwargs,
        )

    @property
    def error_code(self) -> int:
        return self.weather_code

    @error_code.setter
    def error_code(self, value: Union[int, str]) -> None:
        self.weather_code = int(value)
