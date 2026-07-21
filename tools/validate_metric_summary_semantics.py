from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from smart_filter.app_info import APP_VERSION
from smart_filter.ui.metric_summary import build_incident_status_palette, build_metric_summary_values


def main() -> int:
    summary = SimpleNamespace(
        scan_stats={
            "candidates_count": 3098,
            "reader_succeeded_count": 3098,
            "readers_executed_count": 3098,
            "issues_count": 0,
            "content_text_chars_count": 2151089,
        },
        analyzed_candidates_count=3098,
        matched_candidates_count=2321,
        match_occurrences_count=3850,
        no_match_count=777,
        skipped_by_discard_count=0,
        errors=[],
    )
    expected = {
        "candidates": 3098,
        "readers": 3098,
        "matched_files": 2321,
        "characters": 2151089,
        "no_match": 777,
        "errors": 0,
    }
    actual = build_metric_summary_values(summary)
    assert actual == expected, (actual, expected)

    dark_zero = build_incident_status_palette(issues_count=0, is_light=False)
    dark_alert = build_incident_status_palette(issues_count=3, is_light=False)
    light_zero = build_incident_status_palette(issues_count=0, is_light=True)
    light_alert = build_incident_status_palette(issues_count=3, is_light=True)
    assert dark_zero["border"] == "#7f1d1d", dark_zero
    assert dark_alert["border"] == "#ef4444", dark_alert
    assert dark_zero != dark_alert
    assert light_zero["border"] == "#fca5a5", light_zero
    assert light_alert["border"] == "#dc2626", light_alert
    assert light_zero != light_alert

    legacy_import = SimpleNamespace(
        scan_stats={},
        analyzed_candidates_count=12,
        matched_candidates_count=12,
        match_occurrences_count=17,
        no_match_count=0,
        errors=[],
    )
    assert build_metric_summary_values(legacy_import)["readers"] == 12
    assert build_metric_summary_values(legacy_import)["characters"] == 0

    main_app = (PROJECT_ROOT / "smart_filter" / "ui" / "main_app.py").read_text(encoding="utf-8")
    for fragment in (
        '("readers", "◉", "Leídos")',
        '("matched_files", "✓", "Archivos encontrados")',
        '("characters", "≡", "Caracteres")',
        '("no_match", "—", "Sin coincidencia")',
        'for key, value in build_metric_summary_values(summary).items():',
        'base.update(build_incident_status_palette(issues_count=issues_count, is_light=is_light))',
    ):
        assert fragment in main_app, fragment

    labels_start = main_app.index("        labels = (")
    labels_end = main_app.index("        self.metrics_frame =", labels_start)
    labels_block = main_app[labels_start:labels_end]
    for obsolete in ('"Readers"', '"Ocurrencias"', '"Resultados"', '"Descartados"'):
        assert obsolete not in labels_block, obsolete

    assert '"Archivos encontrados"' in main_app
    assert '"Caracteres"' in main_app
    assert '"Ocurrencias"' not in labels_block
    assert '"Sin coincidencia"' in main_app
    assert APP_VERSION, "APP_VERSION vacío"

    print("METRIC_SUMMARY_SEMANTICS_OK")
    print(actual)
    print({"dark_zero": dark_zero, "dark_alert": dark_alert, "light_zero": light_zero, "light_alert": light_alert})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
