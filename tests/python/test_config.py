import json
import pytest
import os
from pathlib import Path
from dcs_log_core.config import load_config, save_config, DEFAULT_CONFIG

def test_load_default_config(tmp_path, monkeypatch):
    """Verify that load_config() returns DEFAULT_CONFIG when no file exists."""
    # Mock config_path to a temp file
    cfg_file = tmp_path / "config.json"
    monkeypatch.setattr("dcs_log_core.config.config_path", lambda: cfg_file)
    
    # When file doesn't exist, should return default config
    cfg = load_config()
    assert cfg == DEFAULT_CONFIG

def test_save_and_load_config(tmp_path, monkeypatch):
    """Verify that configuration can be persisted to disk and reloaded correctly."""
    cfg_file = tmp_path / "config.json"
    monkeypatch.setattr("dcs_log_core.config.config_path", lambda: cfg_file)
    
    custom_cfg = DEFAULT_CONFIG.copy()
    custom_cfg["theme"] = "light"
    custom_cfg["log_path"] = "C:/test.log"
    
    save_config(custom_cfg)
    
    # Check if file exists and has content
    assert cfg_file.exists()
    
    loaded = load_config()
    assert loaded["theme"] == "light"
    assert loaded["log_path"] == "C:/test.log"
    # Ensure other defaults are still there
    assert loaded["window_lines"] == DEFAULT_CONFIG["window_lines"]

def test_load_corrupt_config(tmp_path, monkeypatch):
    """Verify that load_config() falls back to defaults if the JSON file is malformed."""
    cfg_file = tmp_path / "config.json"
    monkeypatch.setattr("dcs_log_core.config.config_path", lambda: cfg_file)
    
    # Write invalid JSON
    cfg_file.write_text("{invalid json", encoding="utf-8")
    
    # Should fallback to defaults
    cfg = load_config()
    assert cfg == DEFAULT_CONFIG

def test_config_merging(tmp_path, monkeypatch):
    """Verify that partial config files are merged with DEFAULT_CONFIG."""
    cfg_file = tmp_path / "config.json"
    monkeypatch.setattr("dcs_log_core.config.config_path", lambda: cfg_file)
    
    # Write config with only one key
    cfg_file.write_text(json.dumps({"theme": "light"}), encoding="utf-8")
    
    # Should merge with defaults
    cfg = load_config()
    assert cfg["theme"] == "light"
    assert cfg["window_lines"] == DEFAULT_CONFIG["window_lines"]

def test_config_dir_linux(tmp_path, monkeypatch):
    """Verify that config directory logic correctly handles Linux paths when mocked."""
    # We mock platform and env, but we mock mkdir so it doesn't actually try to create /tmp on Windows
    monkeypatch.setattr("dcs_log_core.config.platform.system", lambda: "Linux")
    fake_config = tmp_path / "xdg_config"
    monkeypatch.setitem(os.environ, "XDG_CONFIG_HOME", str(fake_config))
    
    from dcs_log_core.config import _config_dir
    d = _config_dir()
    assert str(d).startswith(str(fake_config))
