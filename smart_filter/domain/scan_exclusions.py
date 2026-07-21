from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from file_scan_core import DirectoryExclusionPolicy, DirectoryExclusionRule

BROAD_SCAN_ENABLED_KEY = "broad_scan_safe_enabled"


@dataclass(frozen=True)
class BroadScanOption:
    group_id: str
    setting_key: str
    label: str
    default_enabled: bool
    tooltip: str


BROAD_SCAN_OPTIONS: tuple[BroadScanOption, ...] = (
    BroadScanOption(
        group_id="system_operating_system",
        setting_key="broad_scan_exclude_system",
        label="Sistema operativo",
        default_enabled=True,
        tooltip=(
            "En una raíz de disco excluye carpetas del sistema. "
            "Windows: Windows, $Recycle.Bin, System Volume Information, Recovery, Config.Msi y restos de actualización. "
            "Linux: /proc, /sys, /dev, /run y /lost+found."
        ),
    ),
    BroadScanOption(
        group_id="temporary_and_cache",
        setting_key="broad_scan_exclude_temp_cache",
        label="Temporales y cachés",
        default_enabled=True,
        tooltip=(
            "Excluye temporales, cachés y volcados regenerables. "
            "Windows: Windows\\Temp, AppData\\Local\\Temp, INetCache, CrashDumps y cachés comunes. "
            "Linux: /tmp, /var/tmp, /var/cache, ~/.cache y la papelera local."
        ),
    ),
    BroadScanOption(
        group_id="development_dependencies",
        setting_key="broad_scan_exclude_dev_dependencies",
        label="Dependencias de desarrollo",
        default_enabled=True,
        tooltip=(
            "Excluye por nombre .git, .svn, .hg, node_modules, .venv, venv, env, __pycache__, "
            ".pytest_cache, .mypy_cache, .ruff_cache, .tox, .nox, .gradle, .m2, .npm, .yarn, "
            ".pnpm-store, .idea y .vscode."
        ),
    ),
    BroadScanOption(
        group_id="build_outputs",
        setting_key="broad_scan_exclude_build_outputs",
        label="Salidas de compilación",
        default_enabled=True,
        tooltip=(
            "Excluye por nombre build, dist, target, obj, out, .next, .nuxt, coverage y htmlcov. "
            "Desactivarlo permite buscar artefactos generados o carpetas legítimas con esos nombres."
        ),
    ),
    BroadScanOption(
        group_id="smartfilter_generated_results",
        setting_key="broad_scan_exclude_smartfilter_results",
        label="Resultados generados por Smart Filter",
        default_enabled=True,
        tooltip=(
            "Excluye carpetas de resultados creadas por Smart Filter, como "
            "SmartFilter_Resultados_*, SmartFilterCV_Resultados_* y el prefijo configurado actualmente. "
            "Evita volver a analizar exportaciones anteriores y resultados duplicados."
        ),
    ),
    BroadScanOption(
        group_id="installed_applications",
        setting_key="broad_scan_exclude_installed_apps",
        label="Aplicaciones instaladas",
        default_enabled=False,
        tooltip=(
            "Windows: excluye Program Files y Program Files (x86). "
            "Linux: excluye /opt, /snap, /usr/lib y /usr/local/lib. "
            "Está desactivado por defecto porque pueden contener documentación, configuraciones o registros útiles."
        ),
    ),
    BroadScanOption(
        group_id="shared_system_data",
        setting_key="broad_scan_exclude_shared_system_data",
        label="Datos compartidos del sistema",
        default_enabled=False,
        tooltip=(
            "Windows: excluye ProgramData. Linux: excluye /var/lib. "
            "Está desactivado por defecto porque allí pueden existir configuraciones, bases de datos y registros relevantes."
        ),
    ),
)

BROAD_SCAN_DEFAULTS: dict[str, bool] = {
    BROAD_SCAN_ENABLED_KEY: True,
    **{option.setting_key: option.default_enabled for option in BROAD_SCAN_OPTIONS},
}


@dataclass(frozen=True)
class ScanExclusionContext:
    policy: DirectoryExclusionPolicy
    broad_scan_root_detected: bool
    broad_scan_safe_enabled: bool
    active_group_ids: tuple[str, ...]


def is_broad_scan_root(path: str | Path) -> bool:
    """Returns True for a filesystem/drive root or mounted volume root."""

    candidate = Path(path).expanduser()
    try:
        candidate = candidate.resolve(strict=False)
    except (OSError, RuntimeError, ValueError):
        pass

    try:
        if candidate.anchor and candidate == Path(candidate.anchor):
            return True
    except (OSError, RuntimeError, ValueError):
        pass

    try:
        return candidate.exists() and candidate.is_dir() and os.path.ismount(candidate)
    except OSError:
        return False


def _windows_rules(active_groups: set[str]) -> list[DirectoryExclusionRule]:
    rules: list[DirectoryExclusionRule] = []
    if "system_operating_system" in active_groups:
        rules.append(
            DirectoryExclusionRule.create(
                rule_id="windows_system_roots",
                group_id="system_operating_system",
                reason="Directorio del sistema operativo excluido por Escaneo amplio seguro.",
                relative_path_patterns=(
                    "Windows",
                    "$Recycle.Bin",
                    "System Volume Information",
                    "Recovery",
                    "Config.Msi",
                    "$WinREAgent",
                    "$Windows.~BT",
                    "$Windows.~WS",
                ),
            )
        )
    if "temporary_and_cache" in active_groups:
        rules.append(
            DirectoryExclusionRule.create(
                rule_id="windows_temp_and_cache",
                group_id="temporary_and_cache",
                reason="Temporal o caché regenerable excluido por Escaneo amplio seguro.",
                relative_path_patterns=(
                    "Windows/Temp",
                    "Users/*/AppData/Local/Temp",
                    "Users/*/AppData/Local/Microsoft/Windows/INetCache",
                    "Users/*/AppData/Local/CrashDumps",
                    "Users/*/AppData/Local/*/Cache",
                    "Users/*/AppData/Local/*/Code Cache",
                    "Users/*/AppData/Local/*/GPUCache",
                ),
            )
        )
    if "installed_applications" in active_groups:
        rules.append(
            DirectoryExclusionRule.create(
                rule_id="windows_installed_apps",
                group_id="installed_applications",
                reason="Aplicaciones instaladas excluidas por Escaneo amplio seguro.",
                relative_path_patterns=("Program Files", "Program Files (x86)"),
            )
        )
    if "shared_system_data" in active_groups:
        rules.append(
            DirectoryExclusionRule.create(
                rule_id="windows_shared_system_data",
                group_id="shared_system_data",
                reason="Datos compartidos del sistema excluidos por Escaneo amplio seguro.",
                relative_path_patterns=("ProgramData",),
            )
        )
    return rules


def _linux_rules(active_groups: set[str]) -> list[DirectoryExclusionRule]:
    rules: list[DirectoryExclusionRule] = []
    if "system_operating_system" in active_groups:
        rules.append(
            DirectoryExclusionRule.create(
                rule_id="linux_virtual_system_roots",
                group_id="system_operating_system",
                reason="Directorio virtual o interno de Linux excluido por Escaneo amplio seguro.",
                relative_path_patterns=("proc", "sys", "dev", "run", "lost+found"),
            )
        )
    if "temporary_and_cache" in active_groups:
        rules.append(
            DirectoryExclusionRule.create(
                rule_id="linux_temp_and_cache",
                group_id="temporary_and_cache",
                reason="Temporal o caché regenerable excluido por Escaneo amplio seguro.",
                relative_path_patterns=(
                    "tmp",
                    "var/tmp",
                    "var/cache",
                    "home/*/.cache",
                    "home/*/.local/share/Trash",
                ),
            )
        )
    if "installed_applications" in active_groups:
        rules.append(
            DirectoryExclusionRule.create(
                rule_id="linux_installed_apps",
                group_id="installed_applications",
                reason="Aplicaciones y bibliotecas instaladas excluidas por Escaneo amplio seguro.",
                relative_path_patterns=("opt", "snap", "usr/lib", "usr/local/lib"),
            )
        )
    if "shared_system_data" in active_groups:
        rules.append(
            DirectoryExclusionRule.create(
                rule_id="linux_shared_system_data",
                group_id="shared_system_data",
                reason="Datos compartidos del sistema excluidos por Escaneo amplio seguro.",
                relative_path_patterns=("var/lib",),
            )
        )
    return rules


def _safe_output_prefix(value: Any) -> str:
    clean = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value or "").strip())
    return clean.strip("._-") or "SmartFilter_Resultados"


def _smartfilter_output_rules(
    active_groups: set[str],
    settings: Mapping[str, Any],
) -> list[DirectoryExclusionRule]:
    if "smartfilter_generated_results" not in active_groups:
        return []

    configured_prefix = _safe_output_prefix(settings.get("output_folder_prefix"))
    prefixes = {
        "SmartFilter_Resultados",
        "SmartFilterCV_Resultados",
        configured_prefix,
    }
    patterns = tuple(f"**/{prefix}_*" for prefix in sorted(prefixes, key=str.casefold))
    return [
        DirectoryExclusionRule.create(
            rule_id="smartfilter_generated_results",
            group_id="smartfilter_generated_results",
            reason="Resultado anterior generado por Smart Filter excluido del Escaneo amplio seguro.",
            relative_path_patterns=patterns,
        )
    ]


def _portable_name_rules(active_groups: set[str]) -> list[DirectoryExclusionRule]:
    rules: list[DirectoryExclusionRule] = []
    if "development_dependencies" in active_groups:
        rules.append(
            DirectoryExclusionRule.create(
                rule_id="development_dependencies",
                group_id="development_dependencies",
                reason="Dependencia o metadato de desarrollo excluido por Escaneo amplio seguro.",
                directory_names=(
                    ".git", ".svn", ".hg", "node_modules", ".venv", "venv", "env", "__pycache__",
                    ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox", ".nox", ".gradle", ".m2",
                    ".npm", ".yarn", ".pnpm-store", ".idea", ".vscode",
                ),
            )
        )
    if "build_outputs" in active_groups:
        rules.append(
            DirectoryExclusionRule.create(
                rule_id="build_outputs",
                group_id="build_outputs",
                reason="Salida de compilación o reporte generado excluido por Escaneo amplio seguro.",
                directory_names=("build", "dist", "target", "obj", "out", ".next", ".nuxt", "coverage", "htmlcov"),
            )
        )
    return rules


def build_scan_exclusion_context(
    *,
    root_path: str | Path,
    settings: Mapping[str, Any],
    manual_folder_paths: tuple[Path, ...] | list[Path] = (),
) -> ScanExclusionContext:
    """Builds the effective policy without embedding Smart Filter rules in FileScanCore."""

    rules: list[DirectoryExclusionRule] = []
    if manual_folder_paths:
        rules.append(
            DirectoryExclusionRule.create(
                rule_id="manual_exact_folder_paths",
                group_id="manual_exact_paths",
                reason="Ruta exacta excluida manualmente por el usuario.",
                absolute_paths=manual_folder_paths,
            )
        )

    root_detected = is_broad_scan_root(root_path)
    safe_enabled = bool(settings.get(BROAD_SCAN_ENABLED_KEY, BROAD_SCAN_DEFAULTS[BROAD_SCAN_ENABLED_KEY]))
    active_groups = {
        option.group_id
        for option in BROAD_SCAN_OPTIONS
        if bool(settings.get(option.setting_key, option.default_enabled))
    } if root_detected and safe_enabled else set()

    rules.extend(_smartfilter_output_rules(active_groups, settings))
    rules.extend(_portable_name_rules(active_groups))
    if sys.platform.startswith("win"):
        rules.extend(_windows_rules(active_groups))
    else:
        rules.extend(_linux_rules(active_groups))

    return ScanExclusionContext(
        policy=DirectoryExclusionPolicy.from_rules(rules),
        broad_scan_root_detected=root_detected,
        broad_scan_safe_enabled=bool(root_detected and safe_enabled),
        active_group_ids=tuple(option.group_id for option in BROAD_SCAN_OPTIONS if option.group_id in active_groups),
    )
