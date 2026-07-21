from __future__ import annotations


class SearchCancelledError(RuntimeError):
    """Raised when the caller requests a cooperative search cancellation."""

    def __init__(self, message: str = "Búsqueda cancelada por el usuario.") -> None:
        super().__init__(message)
