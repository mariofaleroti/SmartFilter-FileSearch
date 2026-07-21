from __future__ import annotations

import ast
from pathlib import Path

from smart_filter.app_info import APP_RELEASE_LABEL, APP_RELEASE_STATUS

ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    path = ROOT / relative_path
    if not path.is_file():
        raise AssertionError(f"Falta archivo requerido: {relative_path}")
    return path.read_text(encoding="utf-8")


def _read_app_version() -> str:
    tree = ast.parse(_read("smart_filter/app_info.py"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "APP_VERSION":
                    return str(ast.literal_eval(node.value))
    raise AssertionError("No se encontró APP_VERSION")


def _require_tokens(content: str, tokens: tuple[str, ...], source: str) -> None:
    missing = [token for token in tokens if token not in content]
    if missing:
        raise AssertionError(f"{source} no contiene: {', '.join(missing)}")


def main() -> int:
    version = _read_app_version()
    if APP_RELEASE_STATUS not in {"release_candidate", "stable", "development"}:
        raise AssertionError(f"Canal de versión inválido: {APP_RELEASE_STATUS}")

    readme = _read("README.md")
    _require_tokens(
        readme,
        (
            "# Smart Filter",
            version,
            "## From CV filtering to a general search tool",
            "## SharedCode Cores dependency",
            "## Architecture",
            "## Limitations",
            "docs/USER_GUIDE.md",
            "CHANGELOG.md",
            "README.es.md",
        ),
        "README.md",
    )

    changelog = _read("CHANGELOG.md")
    _require_tokens(changelog, (version, "1.0.30-dev", "1.0.29-dev"), "CHANGELOG.md")

    user_guide = _read("docs/USER_GUIDE.md")
    _require_tokens(
        user_guide,
        ("Palabra/frase", "Categoría", "Destacado", "Equilibrado", "advertencias", "Restaurar predeterminadas"),
        "docs/USER_GUIDE.md",
    )

    category_scope = _read("docs/CATEGORY_TARGET_FIELDS_SCOPE.md")
    _require_tokens(
        category_scope,
        ("campo, columna, clave o encabezado", "Experiencia administrativa requerida", "XLSX/CSV"),
        "docs/CATEGORY_TARGET_FIELDS_SCOPE.md",
    )

    performance = _read("docs/RESOURCE_POLICY_AND_PERFORMANCE_MONITOR.md")
    _require_tokens(
        performance,
        ("Bajo consumo", "Equilibrado", "Alto rendimiento", "Manual técnico", "Backpressure", "psutil.Process"),
        "docs/RESOURCE_POLICY_AND_PERFORMANCE_MONITOR.md",
    )

    checklist = _read("docs/RELEASE_CANDIDATE_CHECKLIST.md")
    _require_tokens(
        checklist,
        ("Máquina virtual limpia", "SmartFilter.exe", "SmartFilterCLI.exe", "APP_VERSION"),
        "docs/RELEASE_CANDIDATE_CHECKLIST.md",
    )

    build_doc = _read("docs/BUILD_AND_RELEASE.md")
    _require_tokens(build_doc, ("Ayuda", "Acerca de", "BUILD_WINDOWS_RELEASE.cmd", "sharedcode-cores"), "docs/BUILD_AND_RELEASE.md")
    if "README_RELEASE.md" in build_doc:
        raise AssertionError("BUILD_AND_RELEASE no debe declarar README dentro del portable")

    help_source = _read("smart_filter/ui/windows/help_window.py")
    _require_tokens(
        help_source,
        (
            "HELP_TABS",
            "Inicio",
            "Criterios",
            "Categorías",
            "Resultados",
            "Rendimiento",
            "Portable",
            "Limitar dónde buscar",
            "Archivos encontrados",
            "Esta versión no incorpora OCR",
            "CTkTabview",
            "CTkScrollableFrame",
        ),
        "help_window.py",
    )
    compile(help_source, "help_window.py", "exec")

    about_source = _read("smart_filter/ui/windows/about_window.py")
    _require_tokens(
        about_source,
        (
            "Qué permite hacer",
            "Formatos compatibles",
            "Modo portable y privacidad",
            "Alcance y limitaciones conocidas",
            "Esta versión no incorpora OCR",
            "APP_RELEASE_LABEL",
        ),
        "about_window.py",
    )
    compile(about_source, "about_window.py", "exec")

    print("DOCUMENTATION_RELEASE_PREP_OK")
    print(f"VERSION_OK {version} status={APP_RELEASE_STATUS} label={APP_RELEASE_LABEL}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
