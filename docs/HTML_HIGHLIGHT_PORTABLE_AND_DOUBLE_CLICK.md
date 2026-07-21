# HTML highlight, portable packaging, and double click

RenderCore is installed through the pinned `sharedcode-cores` wheel. Both PyInstaller specs collect the installed `render_core` package and explicitly validate its bundled `templates/` directory.

The final portable self-check confirms that HTML highlighting works from the packaged CLI executable.

- **Destacado** and the visual double-click mode generate an HTML viewer.
- **Abrir** passes the real original path to the associated application.
- No temporary Office copy is created when opening the original.
