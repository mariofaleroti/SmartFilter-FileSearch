from __future__ import annotations

from pathlib import Path

from smart_filter.app_info import APP_VERSION

ROOT = Path(__file__).resolve().parents[1]
MAIN_APP = ROOT / "smart_filter" / "ui" / "main_app.py"
SETTINGS = ROOT / "smart_filter" / "ui" / "windows" / "settings_window.py"
HELP = ROOT / "smart_filter" / "ui" / "windows" / "help_window.py"
APP_INFO = ROOT / "smart_filter" / "app_info.py"
ACTION_SERVICE = ROOT / "smart_filter" / "services" / "result_action_service.py"


def extract_method(source: str, method_name: str, next_method_name: str) -> str:
    start = source.index(f"    def {method_name}")
    end = source.index(f"    def {next_method_name}", start)
    return source[start:end]


def main() -> None:
    source = MAIN_APP.read_text(encoding="utf-8")
    original_method = extract_method(source, "_open_selected_original", "_open_selected_folder")
    highlighted_method = extract_method(source, "_open_selected_highlight", "_copy_selected_files")

    assert "outcome = open_original(result)" in original_method
    assert "_open_result_by_config" not in original_method
    assert "create_highlight_preview(result)" in highlighted_method
    assert "create_highlighted_file_copy(result)" not in highlighted_method
    assert 'suffix.lower() == ".xlsx"' not in highlighted_method

    settings = SETTINGS.read_text(encoding="utf-8")
    assert '"Acción con doble clic"' in settings
    assert "únicamente al abrir un resultado con doble clic" in settings
    assert "El botón Destacado y el doble clic visual abren el visor HTML; Abrir conserva el archivo original sin crear copias temporales." in settings

    double_click_method = extract_method(source, "_on_double_click", "run")
    configured_method = extract_method(source, "_open_result_by_config", "_open_selected_original")
    assert 'self._open_result_by_config(result, source="Doble clic")' in double_click_method
    assert "create_highlight_preview(result)" in configured_method
    assert "open_original(result)" in configured_method

    action_source = ACTION_SERVICE.read_text(encoding="utf-8")
    office_helper = action_source[action_source.index("def _open_original_office_path"):action_source.index("def open_original", action_source.index("def _open_original_office_path"))]
    original_action = action_source[action_source.index("def open_original"):action_source.index("def open_parent_folder", action_source.index("def open_original"))]
    assert 'OFFICE_ORIGINAL_EXTENSIONS = {".doc", ".docx", ".xls", ".xlsm", ".xlsx"}' in action_source
    assert 'getattr(os, "startfile", None)' in office_helper
    assert '["xdg-open", str(target)]' in office_helper
    assert "target = Path(result.full_path)" in original_action
    assert "_open_original_office_path(target)" in original_action
    assert "shutil.copy" not in original_action
    assert "TEMP_DIR" not in original_action

    help_text = HELP.read_text(encoding="utf-8")
    assert "Abrir: abre siempre la ruta real del archivo original" in help_text
    assert "Destacado: genera una vista HTML temporal con RenderCore" in help_text
    assert "Doble clic: abre el visor HTML destacado o el original según la opción configurada." in help_text

    app_info = APP_INFO.read_text(encoding="utf-8")
    assert f'APP_VERSION = "{APP_VERSION}"' in app_info
    print("OK original Office path opens directly and Destacado uses RenderCore universally")


if __name__ == "__main__":
    main()
