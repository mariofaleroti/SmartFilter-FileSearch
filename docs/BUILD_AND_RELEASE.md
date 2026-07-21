# Build and release

## Development environment

Run `SETUP_DEVELOPMENT_WINDOWS.cmd` on Windows or `SETUP_DEVELOPMENT_LINUX.sh` on Linux. The setup creates `.venv`, installs application dependencies and the pinned `sharedcode-cores` wheel, and executes the validation suite.

Smart Filter does not require a sibling SharedCode folder. `requirements.txt` is the dependency authority for public builds.

## Windows portable

Run:

```bat
BUILD_WINDOWS_RELEASE.cmd
```

The build script:

1. uses `.venv` when available;
2. installs `requirements-dev.txt`;
3. verifies SharedCode Cores 1.0.0 and RenderCore templates;
4. validates factory defaults and source behavior;
5. builds `SmartFilter.exe` and `SmartFilterCLI.exe` with PyInstaller;
6. creates clean external `data/` from `resources/defaults/`;
7. runs `--portable-self-check` against the final executable;
8. validates the archive structure and version.

Output:

```text
release/SmartFilter/
SmartFilter_Portable_v<APP_VERSION>.zip
```

The portable does not include a duplicate README. End-user guidance is available through **Ayuda** and **Acerca de**.
