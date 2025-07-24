"""Compatibility layer for disaster processing modules."""

from WIPServerPy.data.processors.disaster_xml_processor import DisasterProcessor
from WIPServerPy.data.processors.time_utils import TimeProcessor
from WIPServerPy.data.processors.area_code_validator import AreaCodeValidator
from WIPServerPy.data.processors.volcano_processor import VolcanoCoordinateProcessor
from WIPServerPy.data.controllers.disaster_data_processor import DisasterDataProcessor

__all__ = [
    "DisasterProcessor",
    "DisasterDataProcessor",
    "TimeProcessor",
    "AreaCodeValidator",
    "VolcanoCoordinateProcessor",
]
