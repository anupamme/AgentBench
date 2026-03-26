import json
import pytest
from config_loader import load_config
from validator import validate_config


@pytest.fixture
def config_file(tmp_path):
    data = {"host": "example.com", "port": 8080, "timeout": 30, "debug": False}
    p = tmp_path / "config.json"
    p.write_text(json.dumps(data))
    return str(p)


def test_load_and_validate(config_file):
    config = load_config(config_file)
    errors = validate_config(config)
    assert errors == []


def test_timeout_is_int(config_file):
    config = load_config(config_file)
    assert isinstance(config["timeout"], int), f"timeout should be int, got {type(config['timeout'])}"


def test_negative_timeout_detected(tmp_path):
    data = {"host": "h", "port": 80, "timeout": -1}
    p = tmp_path / "cfg.json"
    p.write_text(json.dumps(data))
    config = load_config(str(p))
    errors = validate_config(config)
    assert "timeout must be non-negative" in errors
