# Public repository checklist

Before the first public push:

- [ ] Run `SETUP_DEVELOPMENT_WINDOWS.cmd` or `SETUP_DEVELOPMENT_LINUX.sh`.
- [ ] Run `python -m tools.run_release_validation`.
- [ ] Run `python -m tools.validate_public_repository`.
- [ ] Confirm `git status` does not include `data/`, `runtime/`, `output/`, `.venv/`, `build/`, `dist/`, or `release/`.
- [ ] Confirm no real documents, names, private paths, histories, or generated HTML are present.
- [ ] Build and test the Windows portable on Windows.
- [ ] Create tag `v1.0.31` only after the portable test passes.
- [ ] Attach `SmartFilter_Portable_v1.0.31.zip` and its SHA-256 checksum to the GitHub Release.
