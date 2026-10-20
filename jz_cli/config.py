"""
Config and token path resolution for jz CLI across Windows and macOS/Linux.
"""

from __future__ import annotations

import json
import os
import platform
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional


def get_base_dir() -> Path:
    """
    Get the cross-platform base configuration directory.
    - Windows: %APPDATA%/jz
    - macOS / Linux: ~/.config/jz (or $XDG_CONFIG_HOME/jz)
    """
    system = platform.system().lower()
    if system == "windows":
        app_data = os.environ.get("APPDATA")
        if app_data:
            base = Path(app_data) / "jz"
        else:
            base = Path.home() / "AppData" / "Roaming" / "jz"
    else:
        xdg_config = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config:
            base = Path(xdg_config) / "jz"
        else:
            base = Path.home() / ".config" / "jz"

    base.mkdir(parents=True, exist_ok=True)
    return base


def get_config_path() -> Path:
    """Return the path to config.json."""
    return get_base_dir() / "config.json"


def get_tokens_path() -> Path:
    """
    Return the path to tokens.json for Google Calendar OAuth tokens.
    - Windows: %APPDATA%\\jz\\tokens.json
    - macOS/Linux: ~/.config/jz/tokens.json
    """
    return get_base_dir() / "tokens.json"


def get_client_secrets_path() -> Path:
    """Return default path to Google OAuth credentials.json."""
    return get_base_dir() / "credentials.json"


@dataclass
class AppConfig:
    canvas_url: str = ""
    canvas_token: str = ""
    user_email: str = "student@university.edu"
    user_name: str = "Student"
    active_profile: str = "Default"
    google_credentials_file: Optional[str] = None
    demo_mode: bool = False
    custom_settings: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_canvas_configured(self) -> bool:
        return bool(self.canvas_url and self.canvas_token)

    @property
    def is_google_configured(self) -> bool:
        return get_tokens_path().exists() or bool(self.google_credentials_file and Path(self.google_credentials_file).exists())


def load_config() -> AppConfig:
    """Load user configuration from disk, creating defaults if not present."""
    config_file = get_config_path()
    if not config_file.exists():
        # Default config with demo mode active so users can experience the app immediately
        config = AppConfig(demo_mode=True)
        save_config(config)
        return config

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return AppConfig(
                canvas_url=data.get("canvas_url", ""),
                canvas_token=data.get("canvas_token", ""),
                user_email=data.get("user_email", "student@university.edu"),
                user_name=data.get("user_name", "Student"),
                active_profile=data.get("active_profile", "Default"),
                google_credentials_file=data.get("google_credentials_file"),
                demo_mode=data.get("demo_mode", False),
                custom_settings=data.get("custom_settings", {}),
            )
    except Exception:
        # Fallback to defaults if corrupted
        return AppConfig(demo_mode=True)


def save_config(config: AppConfig) -> None:
    """Persist user configuration to disk."""
    config_file = get_config_path()
    try:
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(asdict(config), f, indent=2)
    except Exception as e:
        print(f"[Error saving config to {config_file}]: {e}")
