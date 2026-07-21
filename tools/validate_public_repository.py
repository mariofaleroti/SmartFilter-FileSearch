from __future__ import annotations

from pathlib import Path

from smart_filter.bootstrap import (
    REQUIRED_SHAREDCODE_VERSION,
    SHAREDCODE_DISTRIBUTION,
    SHAREDCODE_REPOSITORY_URL,
    SHAREDCODE_WHEEL_URL,
)

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert SHAREDCODE_DISTRIBUTION in requirements
    assert SHAREDCODE_WHEEL_URL in requirements
    assert REQUIRED_SHAREDCODE_VERSION == "1.0.0"
    assert SHAREDCODE_REPOSITORY_URL == "https://github.com/mariofaleroti/SharedCode-Cores"

    data_dir = ROOT / "data"
    if data_dir.exists():
        allowed = {"settings.json", "categories.json", "backups"}
        unexpected = {item.name for item in data_dir.iterdir()} - allowed
        assert not unexpected, f"Contenido inesperado en data/: {sorted(unexpected)}"
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for entry in ("data/", "runtime/", "output/", "build/", "dist/", "release/", ".venv/"):
        assert entry in gitignore, entry

    required = (
        "LICENSE",
        "README.md",
        "README.es.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "CODE_OF_CONDUCT.md",
        "SETUP_DEVELOPMENT_WINDOWS.cmd",
        "SETUP_DEVELOPMENT_WINDOWS.ps1",
        "SETUP_DEVELOPMENT_LINUX.sh",
        ".github/ISSUE_TEMPLATE/bug_report.yml",
        ".github/ISSUE_TEMPLATE/feature_request.yml",
        ".github/pull_request_template.md",
    )
    for relative in required:
        assert (ROOT / relative).is_file(), relative

    forbidden_fragments = ("C:\\Users\\", "Nanhok")
    text_suffixes = {".py", ".md", ".txt", ".json", ".toml", ".ps1", ".cmd", ".sh", ".spec", ".yml", ".yaml"}
    generated_directories = {
        ".git",
        ".venv",
        "venv",
        "env",
        "__pycache__",
        "build",
        "dist",
        "release",
        "runtime",
        "output",
        "logs",
        "temp",
        "tmp",
        "data",
        ".pytest_cache",
        ".mypy_cache",
    }

    # Scan only repository source files. Virtual environments and other ignored,
    # generated directories legitimately contain absolute local paths and must
    # never be treated as publishable project content.
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if any(part in generated_directories for part in relative.parts[:-1]):
            continue
        if not path.is_file() or path.suffix.lower() not in text_suffixes:
            continue
        if path.resolve() == Path(__file__).resolve():
            continue
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        for fragment in forbidden_fragments:
            assert fragment not in text, f"{fragment} en {relative}"

    print("PUBLIC_REPOSITORY_OK")
    print(f"SHAREDCODE_PIN_OK {REQUIRED_SHAREDCODE_VERSION}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
