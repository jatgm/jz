"""
Unit tests for jz_cli configuration and path resolution.
"""

from pathlib import Path
from jz_cli.config import AppConfig, get_base_dir, get_config_path, get_tokens_path, load_config, save_config


def test_base_dir_resolution():
    base = get_base_dir()
    assert isinstance(base, Path)
    assert base.exists()


def test_config_paths():
    cfg_path = get_config_path()
    tok_path = get_tokens_path()
    assert cfg_path.name == "config.json"
    assert tok_path.name == "tokens.json"


def test_app_config_defaults():
    config = AppConfig()
    assert config.active_profile == "Default"
    assert not config.is_canvas_configured
