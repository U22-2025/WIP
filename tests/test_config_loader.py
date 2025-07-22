import os
from tempfile import NamedTemporaryFile
from WIPCommonPy.utils.config_loader import ConfigLoader


def test_config_loader_env_expansion(monkeypatch):
    monkeypatch.setenv('TEST_VAR', 'expanded')
    with NamedTemporaryFile('w+', delete=False) as tmp:
        tmp.write('[section]\nkey=${TEST_VAR}')
        tmp.flush()
        loader = ConfigLoader(config_path=tmp.name)
        assert loader.get('section', 'key') == 'expanded'
    os.unlink(tmp.name)
