"""Helpers for running ScreenPhantom inside embedded environments (e.g. Android)."""

from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Optional

import uvicorn

__all__ = ["configure_environment", "start_server", "is_running"]

_server_thread: Optional[threading.Thread] = None
_lock = threading.Lock()


def configure_environment(adb_path: Optional[str] = None) -> None:
    """Configure environment variables for embedded runtimes."""
    if adb_path:
        os.environ["ADB_PATH"] = adb_path


def start_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    log_level: str = "info",
) -> None:
    """Start the uvicorn server in a background thread if not already running."""
    global _server_thread
    with _lock:
        if _server_thread and _server_thread.is_alive():
            return

        def _run() -> None:
            config = uvicorn.Config(
                "screenphantom.app:create_app",
                host=host,
                port=port,
                factory=True,
                log_level=log_level,
            )
            server = uvicorn.Server(config)
            server.run()

        _server_thread = threading.Thread(
            target=_run, name="ScreenPhantomServer", daemon=True
        )
        _server_thread.start()


def is_running() -> bool:
    """Return True if the embedded server thread is alive."""
    return _server_thread is not None and _server_thread.is_alive()
