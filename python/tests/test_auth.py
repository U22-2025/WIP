import hashlib
import hmac
import pytest
from common.utils.auth import WIPAuth


def test_calculate_verify_auth_hash():
    packet_id = 123
    timestamp = 456789
    passphrase = "secret"
    h = WIPAuth.calculate_auth_hash(packet_id, timestamp, passphrase)
    expected = hmac.new(passphrase.encode("utf-8"), f"{packet_id}:{timestamp}:{passphrase}".encode("utf-8"), hashlib.sha256).digest()
    assert h == expected
    assert WIPAuth.verify_auth_hash(packet_id, timestamp, passphrase, h)


def test_auth_init_without_secret(monkeypatch):
    monkeypatch.delenv("WIP_SECRET_KEY", raising=False)
    with pytest.raises(ValueError):
        WIPAuth()
