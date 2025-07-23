import os
import pytest
from WIPCommonPy.utils.auth import WIPAuth


def test_calculate_and_verify_auth_hash():
    packet_id = 123
    timestamp = 456
    passphrase = "secret"
    hash_bytes = WIPAuth.calculate_auth_hash(packet_id, timestamp, passphrase)
    assert isinstance(hash_bytes, bytes)
    assert WIPAuth.verify_auth_hash(packet_id, timestamp, passphrase, hash_bytes)


def test_init_requires_secret_key(monkeypatch):
    monkeypatch.delenv("WIP_SECRET_KEY", raising=False)
    with pytest.raises(ValueError):
        WIPAuth()

    monkeypatch.setenv("WIP_SECRET_KEY", "key")
    auth = WIPAuth()
    assert auth.secret_key == "key"
