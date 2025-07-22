"""Compatibility layer for disaster processing modules."""

from .processors.disaster_xml_processor import DisasterProcessor
from .processors.time_utils import TimeProcessor
from .processors.area_code_validator import AreaCodeValidator
from .processors.volcano_processor import VolcanoCoordinateProcessor
from .controllers.disaster_data_processor import DisasterDataProcessor

__all__ = [
    "DisasterProcessor",
    "DisasterDataProcessor",
    "TimeProcessor",
    "AreaCodeValidator",
    "VolcanoCoordinateProcessor",
]
