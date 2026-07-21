from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    runner_path = ROOT / "smart_filter" / "cli" / "runner.py"
    source = runner_path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    forbidden = (
        "--write-dev-snapshots",
        "smartfilter_step9_cli_results_snapshot.json",
        "Snapshot Paso 9",
        "write_development_snapshots",
        "_copy_contract_to_dev_snapshot",
        "shutil.copy2",
    )
    for token in forbidden:
        assert token not in source, token

    required = (
        "effective_argv",
        "parser.print_help()",
        "return EXIT_OK",
        "return _run_search_cli(namespace, cli_options)",
    )
    for token in required:
        assert token in source, token

    run_cli = next(
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "run_cli"
    )
    assert any(isinstance(node, ast.If) for node in run_cli.body)
    assert (ROOT / "tools" / "write_development_snapshots.py").is_file()

    print("CLI_PRODUCT_BEHAVIOR_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
