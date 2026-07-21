# Contributing

Contributions are welcome when they preserve Smart Filter's privacy, portability, and separation from SharedCode Cores.

## Development setup

Windows:

```bat
SETUP_DEVELOPMENT_WINDOWS.cmd
```

Linux:

```bash
./SETUP_DEVELOPMENT_LINUX.sh
```

Run the validation suite before opening a pull request:

```bash
python -m tools.run_release_validation
python -m tools.validate_public_repository
```

## Project boundaries

SharedCode Cores owns reusable infrastructure. Smart Filter owns search policy, categories, readers, matching, filtering, result semantics, and product-specific GUI/CLI behavior.

Changes that belong to SharedCode Cores should be proposed in its repository instead of being duplicated here.

## Privacy and repository hygiene

Never commit:

- real customer or personal documents;
- names, absolute user paths, histories, or private categories;
- `data/`, `runtime/`, `output/`, logs, highlighted HTML, or temporary files;
- virtual environments, build folders, executables, portable ZIPs, or caches;
- credentials, tokens, or secrets.

Use synthetic documents and neutral paths in tests and screenshots.

## Pull requests

- Keep changes focused.
- Update tests and documentation when behavior changes.
- Preserve the standard JSON contract.
- Avoid unrelated GUI or engine refactors in bug-fix pull requests.
- Describe Windows/Linux impact when platform behavior changes.
