import logging
import time
import pytest
from WIPCommonPy.utils.log_config import UnifiedLogFormatter, LoggerConfig, PerformanceTimer


def test_format_communication_log_full():
    msg = UnifiedLogFormatter.format_communication_log(
        server_name="Srv",
        direction="sent to",
        remote_addr="1.2.3.4",
        remote_port=1234,
        packet_size=10,
        auth_status="auth ok",
        processing_time_ms=12.34,
        packet_details={"foo": "bar", "num": 1}
    )
    expected_lines = [
        "***",
        "Srv:sent to 1.2.3.4:1234",
        "auth ok",
        "送信 パケットバイト数: 10",
        "========",
        "foo: bar",
        "num: 1",
        "処理時間: 12.34ms",
        "***",
    ]
    for line in expected_lines:
        assert line in msg


def test_setup_logger_and_reuse_and_invalid_handler():
    logger = LoggerConfig.setup_logger("test", debug=True)
    assert logger.level == logging.DEBUG
    assert isinstance(logger.handlers[0], logging.StreamHandler)

    handler_count = len(logger.handlers)
    same = LoggerConfig.setup_logger("test", debug=True)
    assert same is logger
    assert len(logger.handlers) == handler_count

    with pytest.raises(ValueError):
        LoggerConfig.setup_logger("x", handler_type="unknown")


def test_specific_helper_loggers():
    dbg = LoggerConfig.setup_debug_helper_logger("foo", debug_enabled=True)
    assert dbg.name == "DebugHelper.foo"
    assert dbg.level == logging.DEBUG

    srv = LoggerConfig.setup_server_logger("mysrv", debug=False)
    assert srv.name == "Server.mysrv"

    cli = LoggerConfig.setup_client_logger("mycli", debug=True)
    assert cli.name == "Client.mycli"


def test_performance_timer_flow(monkeypatch):
    timer = PerformanceTimer()
    times = [100.0, 101.0, 102.5]
    monkeypatch.setattr(time, "time", lambda: times.pop(0))

    timer.start()
    first = timer.mark("step")
    assert "step" in timer.timings
    assert first == 1000.0

    elapsed = timer.get_elapsed_ms()
    assert elapsed == 2500.0

    timer.reset()
    assert timer.start_time is None
    assert timer.timings == {}
