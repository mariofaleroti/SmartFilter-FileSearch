from __future__ import annotations

import re

APP_ID = "smart_filter"
APP_NAME = "Smart Filter"
APP_DISPLAY_NAME = "Smart Filter Archivos"
APP_VERSION = "1.0.32"
APP_TAGLINE = "Filtrado inteligente de archivos"
APP_DESCRIPTION = (
    "Smart Filter busca y filtra archivos por nombre y contenido mediante palabras, categorías inteligentes, "
    "reglas de descarte, exclusiones y tipos de archivo. Funciona de forma local, incluye interfaz gráfica y CLI, "
    "presenta resultados agrupados con ubicaciones y ocurrencias, permite exportarlos y genera vistas HTML destacadas "
    "sin modificar los originales. Analiza contenido textual accesible en PDF, DOCX, XLSX, CSV, TXT, LOG, MD, JSON, XML y HTML. "
    "Esta versión no incorpora OCR."
)

_RC_PATTERN = re.compile(r"-rc\d+$", re.IGNORECASE)
_STABLE_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")


def get_release_status(version: str = APP_VERSION) -> str:
    """Return the manifest status derived from the semantic version string."""

    clean = str(version or "").strip()
    if _RC_PATTERN.search(clean):
        return "release_candidate"
    if _STABLE_PATTERN.fullmatch(clean):
        return "stable"
    return "development"


def get_release_label(version: str = APP_VERSION) -> str:
    """Return the user-facing release label derived from the version."""

    status = get_release_status(version)
    return {
        "release_candidate": "Release candidate",
        "stable": "Versión estable",
        "development": "Versión de desarrollo",
    }[status]


def get_release_channel(version: str = APP_VERSION) -> str:
    """Return a compact channel identifier for reports and manifests."""

    return {
        "release_candidate": "rc",
        "stable": "stable",
        "development": "development",
    }[get_release_status(version)]


APP_RELEASE_STATUS = get_release_status()
APP_RELEASE_LABEL = get_release_label()
APP_RELEASE_CHANNEL = get_release_channel()
