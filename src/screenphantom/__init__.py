"""ScreenPhantom package metadata and helpers."""

from __future__ import annotations

import uvicorn

__all__ = ["__version__", "run_server"]
__version__ = "0.1.0"


def run_server(
    host: str = "0.0.0.0",
    port: int = 8000,
    *,
    reload: bool = False,
    log_level: str = "info",
) -> None:
    """Convenience helper to start the ASGI server."""
    uvicorn.run(
        "screenphantom.app:create_app",
        host=host,
        port=port,
        factory=True,
        reload=reload,
        log_level=log_level,
    )
