# -*- mode: python ; coding: utf-8 -*-
from importlib.util import find_spec
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

block_cipher = None
PROJECT_ROOT = Path.cwd()
pathex = [str(PROJECT_ROOT)]

ctk_datas, ctk_binaries, ctk_hiddenimports = collect_all("customtkinter")
render_datas, render_binaries, render_hiddenimports = collect_all("render_core")

render_spec = find_spec("render_core")
if render_spec is None or not render_spec.submodule_search_locations:
    raise ModuleNotFoundError(
        "RenderCore no está instalado. Ejecutar SETUP_DEVELOPMENT_WINDOWS.cmd."
    )
render_package_root = Path(next(iter(render_spec.submodule_search_locations))).resolve()
render_template_root = render_package_root / "templates"
if not render_template_root.is_dir():
    raise FileNotFoundError(
        f"No se encontraron los templates instalados de RenderCore: {render_template_root}"
    )
render_template_data = (str(render_template_root), "render_core/templates")
if render_template_data not in render_datas:
    render_datas.append(render_template_data)

factory_defaults_root = PROJECT_ROOT / "resources" / "defaults"
if not factory_defaults_root.is_dir():
    raise FileNotFoundError(
        f"No se encontraron los defaults de fábrica: {factory_defaults_root}"
    )
factory_datas = [(str(factory_defaults_root), "resources/defaults")]

hiddenimports = [
    "app_core",
    "cli_core",
    "config_core",
    "date_time_core",
    "file_scan_core",
    "file_system_info_core",
    "gui_core",
    "json_contract_core",
    "logging_core",
    "platform_core",
    "process_runner_core",
    "release_core",
    "render_core",
    "tool_runtime_core",
    "smart_filter.engine.parallel_analysis",
    "smart_filter.engine.candidate_analysis",
    "smart_filter.engine.performance_monitor",
    "smart_filter.engine.resource_policy",
    "smart_filter.services.result_action_service",
    "multiprocessing",
    "multiprocessing.spawn",
    "openpyxl",
    "pypdf",
    "docx",
    "psutil",
    "customtkinter",
    "darkdetect",
] + ctk_hiddenimports + render_hiddenimports

icon_path = PROJECT_ROOT / "assets" / "app_icon.ico"
icon = str(icon_path) if icon_path.exists() else None

a = Analysis(
    ["app.py"],
    pathex=pathex,
    binaries=ctk_binaries + render_binaries,
    datas=ctk_datas + render_datas + factory_datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="SmartFilter",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon,
)
