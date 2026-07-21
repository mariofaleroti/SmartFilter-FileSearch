from __future__ import annotations

import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from smart_filter.bootstrap import ensure_sharedcode_on_path

ensure_sharedcode_on_path()

import smart_filter.domain.scan_exclusions as exclusions
import smart_filter.engine.scan_pipeline as scan_pipeline
from smart_filter.domain.search_form_state import SearchFormState
from smart_filter.domain.search_models import SearchRequest
from smart_filter.services.settings_service import get_default_settings


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="smartfilter_broad_scan_") as temp:
        root = Path(temp)
        fixture = {
            "Documents/visible.txt": "visible",
            "Windows/System32/secret.txt": "secret",
            "node_modules/pkg/index.txt": "dependency",
            "dist/generated.txt": "generated",
            "SmartFilter_Resultados_20260715/resultado.txt": "old result",
            "Program Files/Android/jdk/bin/tool.txt": "legitimate bin",
            "Program Files/App/readme.txt": "installed",
            "ProgramData/App/config.txt": "shared",
        }
        for relative, text in fixture.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")

        settings = get_default_settings()
        settings["broad_scan_safe_enabled"] = True
        settings["broad_scan_exclude_installed_apps"] = False
        settings["broad_scan_exclude_shared_system_data"] = False

        original_root_check = exclusions.is_broad_scan_root
        original_platform = exclusions.sys.platform
        original_get_settings = scan_pipeline.get_settings
        exclusions.is_broad_scan_root = lambda _path: True
        exclusions.sys.platform = "win32"
        scan_pipeline.get_settings = lambda: settings
        try:
            request = SearchRequest(
                form_state=SearchFormState(
                    mode="Carpeta",
                    path=str(root),
                    file_types=["Texto (.txt/.log/.md)"],
                ),
                search_scope="Nombre y contenido",
                file_types=["Texto (.txt/.log/.md)"],
                extensions=[".txt"],
            )
            result = scan_pipeline.scan_file_candidates(request)
        finally:
            exclusions.is_broad_scan_root = original_root_check
            exclusions.sys.platform = original_platform
            scan_pipeline.get_settings = original_get_settings

        names = sorted(candidate.file_name for candidate in result.candidates)
        stats = result.stats.to_dict() if result.stats else {}
        assert names == ["config.txt", "readme.txt", "tool.txt", "visible.txt"], names
        assert stats.get("broad_scan_safe_enabled") is True
        by_group = stats.get("automatic_excluded_directories_by_group", {})
        assert by_group.get("system_operating_system") == 1
        assert by_group.get("development_dependencies") == 1
        assert by_group.get("build_outputs") == 1
        assert by_group.get("smartfilter_generated_results") == 1
        assert stats.get("automatic_excluded_directories_count") == 4

    print("OK: Escaneo amplio seguro poda grupos antes de recorrer subcarpetas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
