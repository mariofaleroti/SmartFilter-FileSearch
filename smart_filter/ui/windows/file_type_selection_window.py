from __future__ import annotations

from typing import Any, Callable

from gui_core import SecondaryWindow, SecondaryWindowConfig

from smart_filter.domain.search_config import ALL_FILE_TYPE_OPTION, get_search_file_type_options
from smart_filter.ui.controllers.search_form_controller import normalize_file_type_selection
from smart_filter.ui.window_icon import apply_window_icon_later


class FileTypeSelectionWindow(SecondaryWindow):
    """Ventana propia de Smart Filter para selección múltiple de tipos.

    Usa la carcasa visual de GuiCore, pero la semántica de tipos/extensiones queda
    en Smart Filter.
    """

    def __init__(
        self,
        parent: Any,
        selected_options: list[str] | None = None,
        font_config: Any | None = None,
        on_accept: Callable[[list[str]], None] | None = None,
        color_theme: str | None = None,
        surface_theme: str | None = None,
        appearance_mode: str | None = None,
    ) -> None:
        self.selected_options = normalize_file_type_selection(selected_options or [])
        self.on_accept = on_accept
        self.variables: dict[str, Any] = {}
        super().__init__(
            parent,
            SecondaryWindowConfig(
                title="Tipos de archivo",
                subtitle="Elegir uno o varios tipos. Smart Filter conserva esta lógica como parte del producto.",
                width=620,
                height=520,
                min_width=560,
                min_height=440,
                modal=True,
                resizable=(False, False),
            ),
            font_config=font_config,
        )
        self._build_content()
        self.add_footer_button("Cancelar", self.close, style="secondary")
        self.add_footer_button("Todos", self.select_all, style="ghost")
        self.add_footer_button("Aceptar", self.accept, style="primary")
        self.apply_visual_preferences(font_config, color_theme, surface_theme, appearance_mode)
        apply_window_icon_later(self)
        apply_window_icon_later(self.content_frame)

    def _build_content(self) -> None:
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(1, weight=1)

        intro = self.ctk.CTkLabel(
            self.content_frame,
            text=(
                "Seleccionar los formatos permitidos para el escaneo. "
                "La opción Todos usa la lista completa de extensiones soportadas."
            ),
            font=self.font_config.tuple("body"),
            text_color="gray",
            justify="left",
            anchor="w",
            wraplength=540,
        )
        intro.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 8))

        frame = self.ctk.CTkScrollableFrame(self.content_frame, fg_color="transparent")
        frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        frame.grid_columnconfigure(0, weight=1)

        for row, option in enumerate(get_search_file_type_options()):
            variable = self.ctk.BooleanVar(value=option in self.selected_options)
            checkbox = self.ctk.CTkCheckBox(
                frame,
                text=option,
                variable=variable,
                font=self.font_config.tuple("body"),
                command=lambda opt=option: self._on_option_changed(opt),
            )
            checkbox.grid(row=row, column=0, sticky="ew", padx=4, pady=5)
            self.variables[option] = variable

    def _on_option_changed(self, option: str) -> None:
        if option == ALL_FILE_TYPE_OPTION and bool(self.variables[option].get()):
            for name, variable in self.variables.items():
                variable.set(name == ALL_FILE_TYPE_OPTION)
            return
        if option != ALL_FILE_TYPE_OPTION and bool(self.variables.get(option).get()):
            all_variable = self.variables.get(ALL_FILE_TYPE_OPTION)
            if all_variable is not None:
                all_variable.set(False)

    def select_all(self) -> None:
        for name, variable in self.variables.items():
            variable.set(name == ALL_FILE_TYPE_OPTION)

    def get_selected_options(self) -> list[str]:
        selected = [name for name, variable in self.variables.items() if bool(variable.get())]
        return normalize_file_type_selection(selected)

    def accept(self) -> None:
        selected = self.get_selected_options()
        if callable(self.on_accept):
            self.on_accept(selected)
        self.close()


def show_file_type_selection_window(
    parent: Any,
    selected_options: list[str] | None = None,
    font_config: Any | None = None,
    on_accept: Callable[[list[str]], None] | None = None,
    color_theme: str | None = None,
    surface_theme: str | None = None,
    appearance_mode: str | None = None,
) -> FileTypeSelectionWindow:
    window = FileTypeSelectionWindow(
        parent,
        selected_options=selected_options,
        font_config=font_config,
        on_accept=on_accept,
        color_theme=color_theme,
        surface_theme=surface_theme,
        appearance_mode=appearance_mode,
    )
    return window
