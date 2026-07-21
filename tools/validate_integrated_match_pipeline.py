from __future__ import annotations

import tempfile
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from smart_filter.bootstrap import ensure_sharedcode_on_path

ensure_sharedcode_on_path()

from smart_filter.domain.search_form_state import SearchFormState
from smart_filter.engine.search_engine import run_search


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="smartfilter_integrated_") as temp_dir:
        root = Path(temp_dir)
        for index in range(80):
            if index == 0:
                text = "administracion facturacion archivo\nadministracion repetida"
            else:
                text = "administracion facturacion archivo" if index % 2 == 0 else "contenido neutro"
            (root / f"fixture_{index:03d}.txt").write_text(text, encoding="utf-8")

        summary = run_search(
            SearchFormState(
                mode="Carpeta",
                path=str(root),
                search_text="administracion",
                category="Ninguna",
                file_types=["Texto (.txt/.log/.md)"],
                search_scope="Nombre y contenido",
            )
        )

        stats = summary.scan_stats
        assert stats.get("execution_pipeline_mode") == "integrated_scan_read_match"
        assert stats.get("match_analysis_integrated") is True
        assert stats.get("match_analysis_separate_pass_eliminated") is True
        assert stats.get("match_analysis_elapsed_seconds") == 0.0
        assert stats.get("reader_workers_count") == 4
        assert stats.get("reader_queue_capacity") == 40
        assert stats.get("candidates_count") == 80
        assert summary.analyzed_candidates_count == 80
        assert summary.matched_candidates_count == 40
        assert summary.match_occurrences_count == 41
        assert summary.no_match_count == 40
        assert stats.get("content_released_after_analysis_count") == 80
        assert stats.get("retained_candidate_content_chars_count") == 0
        assert all(result.candidate.content_text == "" for result in summary.results)
        assert all(result.candidate.content_chars > 0 for result in summary.results)

        print(
            "OK: escaneo, lectura y coincidencias integrados; contenido liberado "
            f"por archivo ({summary.analyzed_candidates_count} candidatos, "
            f"{summary.matched_candidates_count} archivos coincidentes, "
            f"{summary.match_occurrences_count} ocurrencias)."
        )
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
