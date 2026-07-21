from __future__ import annotations

import importlib.metadata
import importlib.util
import os
import sys
from pathlib import Path

SHAREDCODE_DISTRIBUTION = "sharedcode-cores"
REQUIRED_SHAREDCODE_VERSION = "1.0.0"
SHAREDCODE_REPOSITORY_URL = "https://github.com/mariofaleroti/SharedCode-Cores"
SHAREDCODE_RELEASE_URL = f"{SHAREDCODE_REPOSITORY_URL}/releases/tag/v{REQUIRED_SHAREDCODE_VERSION}"
SHAREDCODE_WHEEL_URL = (
    f"{SHAREDCODE_REPOSITORY_URL}/releases/download/v{REQUIRED_SHAREDCODE_VERSION}/"
    f"sharedcode_cores-{REQUIRED_SHAREDCODE_VERSION}-py3-none-any.whl"
)

CORE_PACKAGE_DIRS = {
    "AppCore": "app_core",
    "CliCore": "cli_core",
    "ConfigCore": "config_core",
    "DateTimeCore": "date_time_core",
    "FileScanCore": "file_scan_core",
    "FileSystemInfoCore": "file_system_info_core",
    "GuiCore": "gui_core",
    "JsonContractCore": "json_contract_core",
    "LoggingCore": "logging_core",
    "PlatformCore": "platform_core",
    "ProcessRunnerCore": "process_runner_core",
    "ReleaseCore": "release_core",
    "RenderCore": "render_core",
    "ToolRuntimeCore": "tool_runtime_core",
}

REQUIRED_SHAREDCODE_IMPORTS = tuple(CORE_PACKAGE_DIRS.values())


def project_root() -> Path:
    """Return the external project/runtime root."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def get_installed_sharedcode_version() -> str | None:
    try:
        return importlib.metadata.version(SHAREDCODE_DISTRIBUTION)
    except importlib.metadata.PackageNotFoundError:
        return None


def _missing_sharedcode_imports() -> list[str]:
    return [name for name in REQUIRED_SHAREDCODE_IMPORTS if importlib.util.find_spec(name) is None]


def _candidate_sharedcode_roots() -> list[Path]:
    """Compatibility locations for editable/private development checkouts."""
    root = project_root()
    env_value = os.environ.get("SMARTFILTER_SHAREDCODE_DIR") or os.environ.get("SHAREDCODE_DIR")
    candidates: list[Path] = []
    if env_value:
        candidates.append(Path(env_value).expanduser())
    candidates.extend(
        [
            root.parent / "SharedCode",
            root.parent / "SharedCode-Cores",
            root.parent / "SharedCode_src" / "SharedCode",
            root.parent.parent / "SharedCode",
            root / "SharedCode",
        ]
    )
    return candidates


def find_sharedcode_root() -> Path | None:
    for candidate in _candidate_sharedcode_roots():
        path = candidate.expanduser().resolve()
        if (path / "GuiCore" / "gui_core").is_dir() and (path / "DateTimeCore" / "date_time_core").is_dir():
            return path
    return None


def _add_sharedcode_source_to_path(shared_root: Path) -> None:
    for core_dir in CORE_PACKAGE_DIRS:
        candidate = shared_root / core_dir
        if candidate.is_dir():
            text = str(candidate)
            if text not in sys.path:
                sys.path.insert(0, text)


def ensure_sharedcode_on_path(required: bool = True) -> Path | None:
    """Use the pinned installed package, with source checkout fallback for maintainers.

    Public installations obtain ``sharedcode-cores`` through ``requirements.txt``.
    A sibling checkout or ``SMARTFILTER_SHAREDCODE_DIR`` remains supported only as
    a compatibility path for local development.
    """
    if getattr(sys, "frozen", False):
        return None

    installed_version = get_installed_sharedcode_version()
    missing_imports = _missing_sharedcode_imports()
    if installed_version == REQUIRED_SHAREDCODE_VERSION and not missing_imports:
        return None

    shared_root = find_sharedcode_root()
    if shared_root is not None:
        _add_sharedcode_source_to_path(shared_root)
        if not _missing_sharedcode_imports():
            return shared_root

    if not required:
        return None

    if installed_version and installed_version != REQUIRED_SHAREDCODE_VERSION:
        detail = (
            f"Está instalada la versión {installed_version}, pero Smart Filter "
            f"{__import__('smart_filter.app_info', fromlist=['APP_VERSION']).APP_VERSION} "
            f"requiere {REQUIRED_SHAREDCODE_VERSION}."
        )
    else:
        detail = "No se encontró una instalación válida de SharedCode Cores."

    missing = ", ".join(_missing_sharedcode_imports()) or "versión incompatible"
    raise RuntimeError(
        f"{detail}\nMódulos faltantes: {missing}.\n"
        "Ejecutá SETUP_DEVELOPMENT_WINDOWS.cmd o instalá requirements.txt.\n"
        f"Release requerida: {SHAREDCODE_RELEASE_URL}"
    )
