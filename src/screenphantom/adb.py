"""ADB utility helpers for ScreenPhantom."""

from __future__ import annotations

import asyncio
import os
import subprocess
from dataclasses import dataclass
from typing import List, Sequence


ADB_BINARY = os.environ.get("ADB_PATH", "adb")


class ADBError(RuntimeError):
    """Raised when an ADB command fails."""


def _build_base_command(serial: str | None) -> List[str]:
    cmd = [ADB_BINARY]
    if serial:
        cmd += ["-s", serial]
    return cmd


def _decode_output(blob: bytes | None) -> str:
    if not blob:
        return ""
    return blob.decode("utf-8", errors="ignore").strip()


def _format_failure(result: subprocess.CompletedProcess[bytes]) -> str:
    stdout = _decode_output(result.stdout)
    stderr = _decode_output(result.stderr)
    parts: list[str] = []
    if stdout:
        parts.append(f"stdout: {stdout}")
    if stderr:
        parts.append(f"stderr: {stderr}")
    if not parts:
        parts.append(f"exit code {result.returncode}")
    return "; ".join(parts)


async def _run_async(
    args: Sequence[str],
    *,
    serial: str | None = None,
    capture_output: bool = True,
    timeout: float | None = None,
) -> subprocess.CompletedProcess[bytes]:
    """Run an ADB command asynchronously in a thread."""

    def _runner() -> subprocess.CompletedProcess[bytes]:
        command = _build_base_command(serial) + list(args)
        return subprocess.run(
            command,
            check=False,
            capture_output=capture_output,
            timeout=timeout,
        )

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _runner)


async def adb_shell(
    command: str | Sequence[str],
    *,
    serial: str | None = None,
    timeout: float | None = None,
) -> bytes:
    """Execute an adb shell command and return stdout bytes."""
    if isinstance(command, str):
        args = ["shell", command]
    else:
        args = ["shell"] + list(command)
    result = await _run_async(args, serial=serial, timeout=timeout)
    if result.returncode != 0:
        raise ADBError(
            f"adb shell command failed (code {result.returncode}): {_format_failure(result)}"
        )
    return result.stdout


async def adb_exec_out(
    command: Sequence[str],
    *,
    serial: str | None = None,
    timeout: float | None = None,
) -> bytes:
    """Execute an adb exec-out command and return stdout bytes."""
    args = ["exec-out"] + list(command)
    result = await _run_async(args, serial=serial, timeout=timeout)
    if result.returncode != 0:
        raise ADBError(
            f"adb exec-out failed (code {result.returncode}): {_format_failure(result)}"
        )
    return result.stdout


async def list_devices() -> list[tuple[str, str]]:
    """Return list of (serial, status)."""
    result = await _run_async(["devices"], capture_output=True)
    if result.returncode != 0:
        raise ADBError(f"adb devices failed: {_format_failure(result)}")
    lines = _decode_output(result.stdout).splitlines()
    devices: list[tuple[str, str]] = []
    for line in lines[1:]:
        if not line.strip():
            continue
        serial, status = line.split(maxsplit=1)
        devices.append((serial, status))
    return devices


async def adb_connect(target: str, *, timeout: float | None = None) -> str:
    """Connect to a device over TCP/IP."""
    if not target:
        raise ADBError("Target must not be empty for adb connect")
    result = await _run_async(["connect", target], timeout=timeout)
    if result.returncode != 0:
        raise ADBError(f"adb connect failed: {_format_failure(result)}")
    return _decode_output(result.stdout)


async def adb_disconnect(target: str | None = None) -> str:
    """Disconnect a specific target or all if target is None."""
    args: list[str] = ["disconnect"]
    if target:
        args.append(target)
    result = await _run_async(args)
    if result.returncode != 0:
        raise ADBError(f"adb disconnect failed: {_format_failure(result)}")
    return _decode_output(result.stdout)


async def adb_raw(
    args: Sequence[str],
    *,
    serial: str | None = None,
    timeout: float | None = None,
) -> dict[str, object]:
    """Execute an arbitrary adb command and return structured output."""
    result = await _run_async(args, serial=serial, timeout=timeout)
    return {
        "args": [ADB_BINARY, *([] if not serial else ["-s", serial]), *list(args)],
        "serial": serial,
        "returncode": result.returncode,
        "stdout": _decode_output(result.stdout),
        "stderr": _decode_output(result.stderr),
    }


@dataclass(slots=True)
class ADBController:
    """High level ADB helpers for input and capture."""

    serial: str | None = None

    async def screencap(self) -> bytes:
        """Capture the device screen as PNG bytes."""
        return await adb_exec_out(["screencap", "-p"], serial=self.serial)

    async def send_key(self, key_code: str) -> None:
        await adb_shell(["input", "keyevent", key_code], serial=self.serial)

    async def tap(self, x: int, y: int) -> None:
        await adb_shell(["input", "tap", str(x), str(y)], serial=self.serial)

    async def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> None:
        await adb_shell(
            [
                "input",
                "swipe",
                str(x1),
                str(y1),
                str(x2),
                str(y2),
                str(duration_ms),
            ],
            serial=self.serial,
        )

    async def text(self, text: str) -> None:
        # Escape spaces for adb input text
        escaped = text.replace(" ", "%s")
        await adb_shell(["input", "text", escaped], serial=self.serial)

    async def run_shell(self, args: Sequence[str] | str) -> bytes:
        return await adb_shell(args, serial=self.serial)

    async def enable_tcpip(self, port: int = 5555) -> str:
        """Switch device to TCP/IP mode on the specified port."""
        if port < 1 or port > 65535:
            raise ADBError("Port must be between 1 and 65535")
        result = await _run_async(["tcpip", str(port)], serial=self.serial)
        if result.returncode != 0:
            raise ADBError(f"adb tcpip failed: {_format_failure(result)}")
        return _decode_output(result.stdout)
