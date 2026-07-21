from __future__ import annotations

import ast
from pathlib import Path

from smart_filter.app_info import APP_RELEASE_STATUS, APP_VERSION

ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    path = ROOT / relative_path
    if not path.is_file():
        raise AssertionError(f"Falta archivo requerido: {relative_path}")
    return path.read_text(encoding="utf-8")


def _require_tokens(content: str, tokens: tuple[str, ...], source: str) -> None:
    missing = [token for token in tokens if token not in content]
    if missing:
        raise AssertionError(f"{source} no contiene: {', '.join(missing)}")


def main() -> int:
    if APP_RELEASE_STATUS not in {"release_candidate", "stable", "development"}:
        raise AssertionError(f"Canal de versión inválido: {APP_RELEASE_STATUS}")

    help_source = _read("smart_filter/ui/windows/help_window.py")
    compile(help_source, "help_window.py", "exec")
    tree = ast.parse(help_source)

    _require_tokens(
        help_source,
        (
            'HELP_TABS = ("Inicio", "Criterios", "Categorías", "Resultados", "Rendimiento", "Portable")',
            "CTkTabview",
            "CTkScrollableFrame",
            "Inicio rápido",
            "Tres formas de buscar",
            "Limitar dónde buscar",
            "Administración segura",
            "Archivos encontrados",
            "Caracteres: volumen total de texto procesado",
            "Destacado: genera una vista HTML temporal",
            "incluso para PDF y XLSX",
            "Equilibrado es el punto de partida recomendado",
            "Modo portable y privacidad",
            "Esta versión no incorpora OCR",
            "Smart Filter no envía archivos ni resultados",
        ),
        "help_window.py",
    )

    assert "CTkTextbox" not in help_source, "La ayuda no debe volver al bloque único de texto"
    assert len([node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name.startswith("_build_")]) >= 6

    guide = _read("docs/USER_GUIDE.md")
    for token in (
        "Palabra/frase",
        "Limitar dónde buscar",
        "Restaurar predeterminadas",
        "Archivos encontrados",
        "Destacado",
        "Equilibrado",
        "no incorpora OCR",
    ):
        assert token in guide and token in help_source, token

    readme = _read("README.es.md")
    _require_tokens(
        readme,
        (
            APP_VERSION,
            "Inicio, Criterios, Categorías, Resultados, Rendimiento y Portable",
            "referencia operativa del usuario final",
        ),
        "README.es.md",
    )

    doc = _read("docs/INTEGRATED_HELP_CENTER.md")
    _require_tokens(doc, ("seis áreas", "sin README adicional", "Abrir", "Destacado"), "docs/INTEGRATED_HELP_CENTER.md")

    print("INTEGRATED_HELP_CENTER_OK")
    print(f"VERSION_OK {APP_VERSION}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
