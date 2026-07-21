# Smart Filter

A fast, privacy-focused desktop and CLI application for intelligently searching filenames and document contents across multiple formats.

[Leer en español](README.es.md)

## From CV filtering to a general search tool

Smart Filter began as a focused utility for locating and filtering CV files. As the project evolved, its search engine, category system, readers, result actions, performance controls, and portable workflow grew into a general-purpose local document search application.

Today it can inspect filenames and accessible text in XLSX, PDF, DOCX, CSV, TXT, LOG, Markdown, JSON, XML, HTML, and HTM files. It keeps the original files unchanged and can generate highlighted HTML views for reviewing matches.

## Highlights

- Desktop GUI and automation-friendly CLI.
- Search by word, phrase, category, filename, content, or combined criteria.
- Configurable categories, discard rules, path exclusions, and field/section scope.
- Parallel scanning and bounded content analysis with cooperative cancellation.
- CPU and memory monitoring with automatic and technical resource profiles.
- Open the real original file, its containing folder, or a highlighted HTML view.
- JSON and CSV export using the standard ecosystem contract.
- Windows portable release; source development supported on Windows and Linux.
- Local processing: documents are not uploaded to an external service.

## Privacy

Smart Filter performs searches locally. User state is created under `data/` at runtime and is intentionally excluded from Git. Generated views, logs, and reports are also excluded. Before opening an issue, remove personal paths, names, document text, and other sensitive information from diagnostics.

## Download

Normal users should download the latest Windows portable ZIP from GitHub Releases, extract it, and run `SmartFilter.exe`. Python and SharedCode Cores are already bundled into the executables.

## Development setup

Requirements:

- Python 3.11 or newer.
- Windows or Linux.
- Internet access during dependency installation.

Windows:

```bat
SETUP_DEVELOPMENT_WINDOWS.cmd
```

Linux:

```bash
./SETUP_DEVELOPMENT_LINUX.sh
```

The setup installs the exact SharedCode Cores release tested with Smart Filter:

```text
sharedcode-cores 1.0.0
```

Run the application:

```powershell
.\.venv\Scripts\python.exe app.py
```

Run the CLI:

```powershell
.\.venv\Scripts\python.exe cli.py --help
.\.venv\Scripts\python.exe cli.py --folder "C:\Documents" --query "invoice" --scope "Nombre y contenido"
```

## SharedCode Cores dependency

Smart Filter 1.0.32 pins the public `SharedCode-Cores` release `v1.0.0` in `requirements.txt`. A sibling SharedCode folder is not required. Maintainers may still use an editable source checkout through `SMARTFILTER_SHAREDCODE_DIR` when developing both projects together.

Repository: https://github.com/mariofaleroti/SharedCode-Cores

## Windows portable build

After setup:

```bat
BUILD_WINDOWS_RELEASE.cmd
```

The build runs the validation suite, packages GUI and CLI executables with PyInstaller, executes the portable self-check, and produces:

```text
SmartFilter_Portable_v1.0.32.zip
```

## Architecture

SharedCode Cores supplies reusable infrastructure such as GUI foundations, filesystem scanning, configuration, JSON validation, logging, platform operations, runtime paths, release helpers, and report rendering. Smart Filter keeps its product-specific search policy, categories, readers, matching, filtering, result semantics, and user experience.

## Limitations

- OCR is not included in version 1.0.32.
- Image-only PDFs and JPG/PNG files cannot be searched by content.
- Protected, damaged, locked, or inaccessible files may be reported as incidents.
- Full-disk searches may take several minutes depending on storage and file count.

## Validation

```powershell
python -m tools.run_release_validation
python -m tools.validate_public_repository
```

## Documentation

- [User guide](docs/USER_GUIDE.md)
- [Build and release](docs/BUILD_AND_RELEASE.md)
- [Resource policy and monitoring](docs/RESOURCE_POLICY_AND_PERFORMANCE_MONITOR.md)
- [Category scope](docs/CATEGORY_TARGET_FIELDS_SCOPE.md)
- [Changelog](CHANGELOG.md)

## License

Smart Filter is available under the MIT License.
