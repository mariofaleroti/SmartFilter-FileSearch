from __future__ import annotations

import json
from pathlib import Path

from smart_filter.app_info import APP_RELEASE_LABEL, APP_RELEASE_STATUS, APP_VERSION
from tools.build_release import prepare_release

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    about = (ROOT / "smart_filter" / "ui" / "windows" / "about_window.py").read_text(encoding="utf-8")
    app_info = (ROOT / "smart_filter" / "app_info.py").read_text(encoding="utf-8")
    builder = (ROOT / "tools" / "build_release.py").read_text(encoding="utf-8")
    manifest_source = (ROOT / "smart_filter" / "output" / "tool_manifest.py").read_text(encoding="utf-8")

    for token in (
        "Qué permite hacer",
        "Formatos compatibles",
        "Modo portable y privacidad",
        "Alcance y limitaciones conocidas",
        "Esta versión no incorpora OCR",
        "no envía archivos ni resultados",
        "carpeta SmartFilter completa",
        "APP_RELEASE_LABEL",
    ):
        assert token in about, token

    for file_format in ("PDF", "DOCX", "XLSX", "CSV", "TXT", "LOG", "MD", "JSON", "XML", "HTML"):
        assert f'"{file_format}"' in about, file_format

    assert APP_RELEASE_STATUS == "stable"
    assert APP_RELEASE_LABEL
    assert "get_release_status" in app_info
    assert "Esta versión no incorpora OCR" in app_info
    assert "_write_release_readme" not in builder
    assert "README_RELEASE =" not in builder
    assert "README_RELEASE.md" not in manifest_source
    compile(about, "about_window.py", "exec")

    release_dir = prepare_release(build_executables=False)
    for name in ("README_RELEASE.md", "README.txt", "README.md"):
        assert not (release_dir / name).exists(), name

    manifest = json.loads((release_dir / "tool_manifest.json").read_text(encoding="utf-8"))
    assert manifest["summary"]["version"] == APP_VERSION
    assert manifest["summary"]["status"] == APP_RELEASE_STATUS
    assert manifest["data"]["release"]["status"] == APP_RELEASE_STATUS
    assert "RenderCore" in manifest["data"]["sharedcode"]["cores_used"]
    assert "README_RELEASE.md" not in manifest["data"]["release"]["exported_items"]

    print("ABOUT_RELEASE_INFORMATION_OK")
    print(f"VERSION_OK {APP_VERSION} status={APP_RELEASE_STATUS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
