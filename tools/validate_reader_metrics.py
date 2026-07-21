from __future__ import annotations

import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from smart_filter.bootstrap import ensure_sharedcode_on_path

ensure_sharedcode_on_path()

from smart_filter.domain.search_form_state import SearchFormState
from smart_filter.engine import scan_pipeline
from smart_filter.engine.search_engine import run_search
from smart_filter.readers.base import build_reader_result


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="smartfilter_reader_metrics_") as temp:
        root = Path(temp)
        (root / "ok.txt").write_text("correcto", encoding="utf-8")
        (root / "broken.txt").write_text("fallo", encoding="utf-8")

        original_reader = scan_pipeline.read_file_content

        def controlled_reader(path: str | Path, *, max_size_bytes: int | None = None):
            del max_size_bytes
            item = Path(path)
            if item.name == "broken.txt":
                return build_reader_result(
                    item,
                    reader_name="test_reader",
                    status="reader_error",
                    error="Falla controlada",
                )
            return build_reader_result(item, reader_name="test_reader", text="correcto")

        scan_pipeline.read_file_content = controlled_reader
        try:
            summary = run_search(
                SearchFormState(
                    mode="Carpeta",
                    path=str(root),
                    search_text="correcto",
                    search_scope="Solo contenido",
                    file_types=["Texto (.txt/.log/.md)"],
                )
            )
        finally:
            scan_pipeline.read_file_content = original_reader

        stats = summary.scan_stats
        assert stats.get("readers_executed_count") == 2
        assert stats.get("reader_succeeded_count") == 1
        assert stats.get("reader_controlled_error_count") == 1
        assert stats.get("reader_worker_failed_count") == 0
        assert stats.get("reader_failed_count") == 1
        assert stats.get("reader_task_succeeded_count") == 2
        assert stats.get("reader_task_failed_count") == 0

    print("OK: métricas separan lecturas correctas, errores controlados y fallos del trabajador.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
