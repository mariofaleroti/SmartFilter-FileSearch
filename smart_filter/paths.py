from __future__ import annotations

import sys
from pathlib import Path

from .bootstrap import project_root

PROJECT_ROOT = project_root()


def bundled_root() -> Path:
    """Return the root that contains immutable files bundled by PyInstaller."""

    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS")).resolve()
    return PROJECT_ROOT


BUNDLED_ROOT = bundled_root()
RESOURCES_DIR = BUNDLED_ROOT / "resources"
DEFAULTS_DIR = RESOURCES_DIR / "defaults"
FACTORY_SETTINGS_PATH = DEFAULTS_DIR / "settings.json"
FACTORY_CATEGORIES_PATH = DEFAULTS_DIR / "categories.json"

DATA_DIR = PROJECT_ROOT / "data"
ASSETS_DIR = PROJECT_ROOT / "assets"
OUTPUT_DIR = PROJECT_ROOT / "output"
RUNTIME_DIR = PROJECT_ROOT / "runtime"
LOGS_DIR = RUNTIME_DIR / "logs"
TEMP_DIR = RUNTIME_DIR / "temp"

SETTINGS_PATH = DATA_DIR / "settings.json"
CATEGORIES_PATH = DATA_DIR / "categories.json"


def ensure_project_directories() -> None:
    for path in (DATA_DIR, ASSETS_DIR, OUTPUT_DIR, RUNTIME_DIR, LOGS_DIR, TEMP_DIR):
        path.mkdir(parents=True, exist_ok=True)
