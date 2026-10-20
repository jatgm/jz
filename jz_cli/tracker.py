"""
File tracking, manifest registry, and zero-trace uninstallation for jz CLI.
Keeps an explicit inventory of all configuration, tokens, credentials, and caches.
"""

from __future__ import annotations

import datetime
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from jz_cli.config import (
    get_base_dir,
    get_client_secrets_path,
    get_config_path,
    get_tokens_path,
)


@dataclass
class TrackedPath:
    name: str
    description: str
    path: Path
    is_dir: bool = False

    @property
    def exists(self) -> bool:
        return self.path.exists()

    @property
    def size_bytes(self) -> int:
        if not self.exists:
            return 0
        if self.is_dir:
            total = 0
            for p in self.path.rglob("*"):
                if p.is_file():
                    total += p.stat().st_size
            return total
        return self.path.stat().st_size

    @property
    def modified_time(self) -> Optional[datetime.datetime]:
        if not self.exists:
            return None
        return datetime.datetime.fromtimestamp(self.path.stat().st_mtime)


def get_tracked_items() -> List[TrackedPath]:
    """Return explicit list of all paths tracked and managed by jz."""
    base = get_base_dir()
    return [
        TrackedPath(
            name="Configuration Directory",
            description="Root application data and settings directory",
            path=base,
            is_dir=True,
        ),
        TrackedPath(
            name="Config File",
            description="User configuration, Canvas endpoint, profile settings",
            path=get_config_path(),
        ),
        TrackedPath(
            name="OAuth Tokens",
            description="Google Calendar OAuth2 access and refresh tokens",
            path=get_tokens_path(),
        ),
        TrackedPath(
            name="OAuth Credentials",
            description="Google Calendar API client secret JSON",
            path=get_client_secrets_path(),
        ),
        TrackedPath(
            name="Calendar Cache",
            description="Cached calendar events for fast startup and offline view",
            path=base / "cache_calendar.json",
        ),
        TrackedPath(
            name="Canvas Cache",
            description="Cached assignments and enrolled courses",
            path=base / "cache_canvas.json",
        ),
        TrackedPath(
            name="Manifest File",
            description="File inventory registry",
            path=base / "manifest.json",
        ),
    ]


def record_manifest() -> None:
    """Record current tracked files into manifest.json."""
    base = get_base_dir()
    manifest_file = base / "manifest.json"
    items = get_tracked_items()

    data = {
        "updated_at": datetime.datetime.now().isoformat(),
        "files": [
            {
                "name": item.name,
                "path": str(item.path),
                "exists": item.exists,
                "size_bytes": item.size_bytes,
            }
            for item in items
        ],
    }
    try:
        import json
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def uninstall_application(remove_package: bool = False) -> Tuple[bool, List[str]]:
    """
    Completely removes all files, tokens, and directories created by jz without leaving a trace.
    If remove_package is True, also uninstalls the jz-cli python package via pip.
    """
    deleted_items: List[str] = []
    base = get_base_dir()

    # 1. Remove all files inside base directory and the directory itself
    if base.exists():
        try:
            for item in list(base.glob("*")):
                if item.is_file():
                    item.unlink()
                    deleted_items.append(f"Deleted file: {item}")
                elif item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                    deleted_items.append(f"Deleted directory: {item}")

            # Remove base directory
            base.rmdir()
            deleted_items.append(f"Deleted root config directory: {base}")
        except Exception as e:
            # Force rmtree if rmdir failed
            shutil.rmtree(base, ignore_errors=True)
            deleted_items.append(f"Removed base directory: {base} ({e})")

    # 2. Optionally uninstall python package
    if remove_package:
        try:
            cmd = [sys.executable, "-m", "pip", "uninstall", "-y", "jz-cli"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                deleted_items.append("Uninstalled 'jz-cli' package from Python environment.")
            else:
                deleted_items.append(f"Pip uninstall note: {result.stderr.strip() or result.stdout.strip()}")
        except Exception as e:
            deleted_items.append(f"Failed to run pip uninstall: {e}")

    return True, deleted_items
