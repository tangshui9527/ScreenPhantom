"""CLI entry point for ScreenPhantom."""

from __future__ import annotations

import argparse
from . import run_server


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ScreenPhantom ADB remote control server")
    parser.add_argument("--host", default="0.0.0.0", help="Host interface to bind")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind")
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable autoreload (development only)",
    )
    parser.add_argument(
        "--log-level",
        default="info",
        help="Log level passed to uvicorn",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_server(
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level,
    )


if __name__ == "__main__":
    main()
