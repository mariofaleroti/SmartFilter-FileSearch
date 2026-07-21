from __future__ import annotations

from typing import Any

from gui_core import require_customtkinter

ctk = require_customtkinter()


class SmartTooltip:
    """Tooltip liviano para aclaraciones cortas sin ocupar espacio fijo."""

    def __init__(
        self,
        widget: Any,
        text: str,
        *,
        delay_ms: int = 1000,
        visible_ms: int = 4200,
        wraplength: int = 320,
        font_config: Any = None,
    ) -> None:
        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms
        self.visible_ms = visible_ms
        self.wraplength = wraplength
        self.font_config = font_config
        self._after_id: str | None = None
        self._hide_after_id: str | None = None
        self._window: Any = None
        self._bind_widget_tree(widget)

    def _bind_widget_tree(self, widget: Any) -> None:
        try:
            widget.bind("<Enter>", self._schedule, add="+")
            widget.bind("<Leave>", self._hide, add="+")
            widget.bind("<ButtonPress>", self._hide, add="+")
            widget.bind("<ButtonRelease>", self._hide, add="+")
            widget.bind("<FocusIn>", self._hide, add="+")
            widget.bind("<MouseWheel>", self._hide, add="+")
            widget.bind("<B1-Motion>", self._hide, add="+")
            for child in widget.winfo_children():
                self._bind_widget_tree(child)
        except Exception:
            pass

    def _schedule(self, _event: Any = None) -> None:
        self._cancel()
        try:
            self._after_id = self.widget.after(self.delay_ms, self._show)
        except Exception:
            self._after_id = None

    def _cancel(self) -> None:
        if self._after_id is None:
            return
        try:
            self.widget.after_cancel(self._after_id)
        except Exception:
            pass
        self._after_id = None

    def _cancel_hide_timer(self) -> None:
        if self._hide_after_id is None:
            return
        target = self._window or self.widget
        try:
            target.after_cancel(self._hide_after_id)
        except Exception:
            pass
        self._hide_after_id = None

    def _show(self) -> None:
        if self._window is not None:
            return
        try:
            x = self.widget.winfo_rootx() + self.widget.winfo_width() + 12
            y = self.widget.winfo_rooty()
            window = ctk.CTkToplevel(self.widget)
            window.withdraw()
            window.overrideredirect(True)
            window.attributes("-topmost", True)
            frame = ctk.CTkFrame(
                window,
                fg_color="#111827",
                border_color="#334155",
                border_width=1,
                corner_radius=8,
            )
            frame.pack(fill="both", expand=True)
            label = ctk.CTkLabel(
                frame,
                text=self.text,
                justify="left",
                anchor="w",
                wraplength=self.wraplength,
                font=self.font_config.tuple("small") if self.font_config else None,
                text_color="#e5e7eb",
            )
            label.pack(padx=10, pady=7)
            window.update_idletasks()
            try:
                screen_width = window.winfo_screenwidth()
                if x + window.winfo_reqwidth() > screen_width - 12:
                    x = self.widget.winfo_rootx() + 18
                    y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8
            except Exception:
                pass
            window.geometry(f"+{x}+{y}")
            window.deiconify()
            self._window = window
            self._cancel_hide_timer()
            try:
                self._hide_after_id = window.after(self.visible_ms, self._hide)
            except Exception:
                self._hide_after_id = None
        except Exception:
            self._window = None

    def _hide(self, _event: Any = None) -> None:
        self._cancel()
        self._cancel_hide_timer()
        if self._window is None:
            return
        try:
            self._window.destroy()
        except Exception:
            pass
        self._window = None
