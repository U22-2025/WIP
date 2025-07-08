import logging
from unittest import mock
import importlib

import WIP_Server.scripts.update_weather_data as upd


def test_logging_debug(caplog):
    def dummy_get_data(area_codes, debug=False, save_to_redis=False):
        logger = logging.getLogger(upd.__name__)
        if debug:
            logger.debug("dummy get_data called")
        return []

    with mock.patch.object(upd, "get_data", side_effect=dummy_get_data):
        with caplog.at_level(logging.DEBUG):
            upd.update_redis_weather_data(debug=True, area_codes=["123"])

    messages = [r.getMessage() for r in caplog.records]
    assert "気象情報の取得を開始します" in messages
    assert "dummy get_data called" in messages


def test_logging_no_debug(caplog):
    def dummy_get_data(area_codes, debug=False, save_to_redis=False):
        logger = logging.getLogger(upd.__name__)
        if debug:
            logger.debug("dummy called")
        return []

    with mock.patch.object(upd, "get_data", side_effect=dummy_get_data):
        with caplog.at_level(logging.DEBUG):
            upd.update_redis_weather_data(debug=False, area_codes=["123"])

    messages = [r.getMessage() for r in caplog.records]
    assert "dummy called" not in messages
    assert "気象情報の取得を開始します" not in messages
