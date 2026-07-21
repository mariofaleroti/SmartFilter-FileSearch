from __future__ import annotations

from smart_filter.bootstrap import ensure_sharedcode_on_path

ensure_sharedcode_on_path()

from smart_filter.domain.search_config import (
    CATEGORY_SEARCH_MODE_ALL_CONTENT,
    CATEGORY_SEARCH_MODE_TARGET_FIELDS,
)
from smart_filter.domain.search_form_state import SearchFormState
from smart_filter.domain.search_models import FileCandidate, SearchRequest
from smart_filter.engine.candidate_analysis import CandidateAnalyzer
from smart_filter.engine.category_scope import extract_category_content_scope
from smart_filter.engine.match_engine import evaluate_candidate
from smart_filter.engine.parallel_analysis import AnalysisBatchItem, analyze_candidate_batch_locally


def _request(mode: str) -> SearchRequest:
    state = SearchFormState(
        mode="Carpeta",
        path="demo",
        category="administracion",
        search_scope="Nombre y contenido",
        file_types=["Texto (.txt/.log/.md)"],
        source="category_target_fields_validator",
    )
    return SearchRequest(
        form_state=state,
        category_name="administracion",
        category_terms=[
            "administracion",
            "archivo",
            "documentacion",
            "facturacion",
            "atencion al cliente",
        ],
        search_scope="Nombre y contenido",
        file_types=["Texto (.txt/.log/.md)"],
        extensions=[".txt", ".xlsx"],
        category_search_mode=mode,
        category_target_fields=["Experiencia"],
    )


def _candidate(name: str, content: str, extension: str = ".txt") -> FileCandidate:
    return FileCandidate(
        full_path=f"demo/{name}",
        file_name=name,
        extension=extension,
        folder_path="demo",
        content_text=content,
        source="category_target_fields_validator",
        content_reader="text_reader" if extension == ".txt" else "xlsx_reader",
        content_status="ok",
        content_chars=len(content),
    )


def _result_signature(outcome) -> list[tuple[tuple[str, ...], str, str]]:
    return [
        (
            tuple(result.matched_terms),
            result.location_label,
            result.preview_text,
        )
        for result in outcome.results
    ]


def main() -> int:
    limited_request = _request(CATEGORY_SEARCH_MODE_TARGET_FIELDS)
    full_request = _request(CATEGORY_SEARCH_MODE_ALL_CONTENT)

    multiline = _candidate(
        "Administracion_general.txt",
        "\n".join(
            [
                "PERFIL",
                "Archivo y documentación administrativa.",
                "EXPERIENCIA LABORAL",
                "Atención al cliente y facturación.",
                "EDUCACIÓN",
                "Administración de empresas.",
            ]
        ),
    )

    scope = extract_category_content_scope(multiline.content_text, ["Experiencia"])
    assert scope.text == "Atención al cliente y facturación."
    assert [segment.line_number for segment in scope.segments] == [4]

    limited = CandidateAnalyzer(limited_request).analyze(multiline)
    assert limited.no_match_count == 0
    assert len(limited.results) == 1
    result = limited.results[0]
    assert result.matched_terms == ["facturacion", "atencion al cliente"]
    assert result.occurrence_count == 1
    assert result.location_label == "Línea 4"
    assert "Atención al cliente" in result.preview_text
    assert "archivo" not in [term.casefold() for term in result.matched_terms]
    assert "administracion" not in [term.casefold() for term in result.matched_terms]

    # El nombre del archivo y las secciones ajenas no deben rescatar un resultado
    # cuando la categoría está limitada a Experiencia.
    outside_only = _candidate(
        "Administracion_archivo.txt",
        "PERFIL\nArchivo administrativo.\nHABILIDADES\nAdministración.",
    )
    outside_outcome = CandidateAnalyzer(limited_request).analyze(outside_only)
    assert outside_outcome.no_match_count == 1
    assert not outside_outcome.results
    assert evaluate_candidate(outside_only, limited_request).matched is False

    # Los lectores de Excel/Word pueden entregar una sola línea. El alcance debe
    # reconocer igualmente la sección y detenerse en la siguiente cabecera.
    flattened = _candidate(
        "CV_Administracion.xlsx",
        (
            "Curriculum Vitae Nombre Ana Resumen Perfil con experiencia en archivo "
            "Experiencia Atención al cliente Facturación "
            "Habilidades Excel Administración"
        ),
        extension=".xlsx",
    )
    scalar_scope = extract_category_content_scope(
        "Cargo\nAdministrativo\nExperiencia\nVentas",
        ["Cargo"],
    )
    assert scalar_scope.text == "Administrativo"

    flat_scope = extract_category_content_scope(flattened.content_text, ["Experiencia"])
    assert flat_scope.text == "Atención al cliente Facturación"
    flat_outcome = CandidateAnalyzer(limited_request).analyze(flattened)
    assert flat_outcome.no_match_count == 0
    assert flat_outcome.results[0].matched_terms == ["facturacion", "atencion al cliente"]
    assert "Archivo" not in flat_outcome.results[0].preview_text
    assert "Administración" not in flat_outcome.results[0].preview_text

    # Con Todo el contenido se conserva el comportamiento histórico.
    full_outcome = CandidateAnalyzer(full_request).analyze(multiline)
    full_terms = {term.casefold() for term in full_outcome.results[0].matched_terms}
    assert {"administracion", "archivo", "documentacion", "facturacion", "atencion al cliente"} <= full_terms
    assert full_outcome.results[0].occurrence_count == 3

    # El mismo analizador se usa dentro de multiprocessing. La salida local del
    # límite de proceso debe ser idéntica a la ruta normal.
    batch = (AnalysisBatchItem(sequence=1, candidate=multiline),)
    process_outcome = analyze_candidate_batch_locally(limited_request, batch)
    assert len(process_outcome.items) == 1
    assert process_outcome.items[0].outcome is not None
    assert _result_signature(process_outcome.items[0].outcome) == _result_signature(limited)

    print("CATEGORY_TARGET_FIELDS_SCOPE_OK")
    print(
        {
            "target_fields": limited_request.category_target_fields,
            "limited_terms": result.matched_terms,
            "limited_occurrences": result.occurrence_count,
            "full_terms": sorted(full_terms),
            "flat_scope": flat_scope.text,
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
