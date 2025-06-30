from .response import Response
from .extended_field import ExtendedField
from typing import Optional, Union, Dict, Any

class ErrorResponse(Response):
    """Type7 Error packet with optional source information."""

    def __init__(
        self,
        *,
        version: int = 1,
        packet_id: int = 0,
        error_code: int = 0,
        timestamp: Optional[int] = None,
        ex_field: Optional[Union[Dict[str, Any], ExtendedField]] = None,
        **kwargs,
    ) -> None:
        super().__init__(
            version=version,
            packet_id=packet_id,
            type=7,
            ex_flag=1,
            timestamp=timestamp or 0,
            weather_code=error_code,
            ex_field=ex_field,
            **kwargs,
        )

    @property
    def error_code(self) -> int:
        return self.weather_code

    @error_code.setter
    def error_code(self, value: int) -> None:
        self.weather_code = value

