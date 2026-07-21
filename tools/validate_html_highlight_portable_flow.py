from __future__ import annotations

import tempfile
from pathlib import Path

from smart_filter.bootstrap import ensure_sharedcode_on_path

ensure_sharedcode_on_path()

from openpyxl import Workbook
from pypdf import PdfWriter

from smart_filter.app_info import APP_VERSION
from smart_filter.domain.search_models import FileCandidate, SearchResult
from smart_filter.services.document_highlight_service import render_document_highlight
from smart_filter.services.settings_service import _normalize_open_result_mode

ROOT = Path(__file__).resolve().parents[1]


def _build_result(path: Path, *, reader: str, location: str) -> SearchResult:
    return SearchResult(
        index=1,
        candidate=FileCandidate.from_path(
            path,
            source="html_highlight_validation",
            content_reader=reader,
            content_status="ok",
        ),
        match_source="Contenido",
        matches="Coincidencia: administracion",
        matched_terms=["administracion"],
        category_name="administracion",
        location_label=location,
        preview_text="administracion",
        occurrence_count=1,
        match_locations=[
            {
                "location_label": location,
                "matched_terms": ["administracion"],
                "preview_text": "administracion",
            }
        ],
    )


def _assert_rendered(path: Path, reader: str, location: str, output: Path) -> None:
    outcome = render_document_highlight(_build_result(path, reader=reader, location=location), output)
    assert outcome.output_path.is_file(), outcome
    html = outcome.output_path.read_text(encoding="utf-8")
    for marker in (
        "Smart Filter · Documento destacado",
        "administracion",
        "RenderCore",
    ):
        assert marker in html, marker


def main() -> int:
    assert APP_VERSION, "APP_VERSION vacío"
    assert _normalize_open_result_mode("Abrir copia destacada") == "Abrir vista destacada HTML"
    assert _normalize_open_result_mode("Abrir original") == "Abrir original"

    main_app = (ROOT / "smart_filter" / "ui" / "main_app.py").read_text(encoding="utf-8")
    open_policy_start = main_app.index("    def _open_result_by_config")
    open_policy_end = main_app.index("    def _open_selected_original", open_policy_start)
    open_policy = main_app[open_policy_start:open_policy_end]
    assert "create_highlight_preview(result)" in open_policy
    assert "create_highlighted_file_copy" not in open_policy
    assert "Abrir vista destacada HTML" in open_policy

    original_start = main_app.index("    def _open_selected_original")
    original_end = main_app.index("    def _open_selected_folder", original_start)
    original_policy = main_app[original_start:original_end]
    assert "open_original(result)" in original_policy
    assert "create_highlight_preview" not in original_policy

    for spec_name in ("SmartFilter.spec", "SmartFilterCLI.spec"):
        spec = (ROOT / spec_name).read_text(encoding="utf-8")
        assert 'render_spec = find_spec("render_core")' in spec
        assert 'render_package_root = Path(next(iter(render_spec.submodule_search_locations))).resolve()' in spec
        assert 'render_template_root = render_package_root / "templates"' in spec
        assert '(str(render_template_root), "render_core/templates")' in spec

    with tempfile.TemporaryDirectory(prefix="smartfilter_html_highlight_") as temp_dir:
        temp = Path(temp_dir)

        workbook_path = temp / "administracion.xlsx"
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "Datos"
        worksheet.append(["Área", "Detalle"])
        worksheet.append(["Administracion", "Liquidación de sueldos"])
        workbook.save(workbook_path)
        workbook.close()
        _assert_rendered(
            workbook_path,
            "xlsx_reader",
            "Hoja Datos · Fila 2",
            temp / "xlsx_destacado.html",
        )

        pdf_path = temp / "administracion.pdf"
        writer = PdfWriter()
        writer.add_blank_page(width=612, height=792)
        with pdf_path.open("wb") as stream:
            writer.write(stream)
        _assert_rendered(
            pdf_path,
            "pdf_reader",
            "Página 1",
            temp / "pdf_destacado.html",
        )

    print("HTML_HIGHLIGHT_PORTABLE_FLOW_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
