from __future__ import annotations

from pathlib import Path


def read_pdf_text(file_path: str | Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - depends on local environment.
        raise RuntimeError("Falta dependencia pypdf para leer archivos .pdf") from exc

    extracted_text: list[str] = []
    reader = PdfReader(str(file_path))

    if getattr(reader, "is_encrypted", False):
        decrypt_result = reader.decrypt("")
        if decrypt_result == 0:
            raise ValueError("PDF protegido o cifrado")

    for page in reader.pages:
        try:
            page_text = page.extract_text() or ""
        except Exception:
            continue
        if page_text.strip():
            extracted_text.append(page_text.strip())

    return "\n".join(extracted_text)
