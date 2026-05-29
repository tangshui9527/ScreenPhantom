"""FastAPI application providing remote control over ADB."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shlex
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, PositiveInt

from .adb import (
    ADBController,
    ADBError,
    adb_connect,
    adb_disconnect,
    adb_raw,
    list_devices,
)
from .streamer import mjpeg_stream

SRC_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = SRC_DIR.parent

STATIC_DIR = (REPO_ROOT / "web" / "static")
TEMPLATE_DIR = (REPO_ROOT / "web" / "templates")

if not STATIC_DIR.exists():
    STATIC_DIR = SRC_DIR / "web" / "static"
if not TEMPLATE_DIR.exists():
    TEMPLATE_DIR = SRC_DIR / "web" / "templates"

app = FastAPI(title="ScreenPhantom", version="0.1.0")
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class BaseRequest(BaseModel):
    serial: Optional[str] = Field(
        default=None, description="Optional device serial when multiple devices are connected"
    )


class TapRequest(BaseRequest):
    x: PositiveInt
    y: PositiveInt


class SwipeRequest(BaseRequest):
    start_x: PositiveInt = Field(alias="x1")
    start_y: PositiveInt = Field(alias="y1")
    end_x: PositiveInt = Field(alias="x2")
    end_y: PositiveInt = Field(alias="y2")
    duration_ms: PositiveInt = Field(default=300, description="Duration of swipe in milliseconds")

    class Config:
        allow_population_by_field_name = True


class KeyRequest(BaseRequest):
    key: str = Field(description="ADB keyevent code, e.g. KEYCODE_HOME")


class TextRequest(BaseRequest):
    text: str = Field(description="Text to inject on the device")


class ShellRequest(BaseRequest):
    command: str = Field(description="Raw adb shell command to execute on device")


class ConnectRequest(BaseModel):
    target: str = Field(description="Target in host:port format or an RFC-3986 style URI")
    timeout: Optional[float] = Field(
        default=None,
        description="Optional timeout in seconds",
        ge=0.1,
        le=30.0,
    )


class DisconnectRequest(BaseModel):
    target: Optional[str] = Field(
        default=None,
        description="Optional target; omit to disconnect all TCP/IP sessions",
    )


class TcpipRequest(BaseRequest):
    port: int = Field(default=5555, ge=1, le=65535)


class DebugADBRequest(BaseModel):
    command: str = Field(
        description="adb arguments (omit leading 'adb'), e.g. 'devices -l'"
    )
    serial: Optional[str] = Field(
        default=None, description="Optional target serial for the command"
    )
    timeout: Optional[float] = Field(
        default=None,
        ge=0.1,
        le=60.0,
        description="Optional timeout in seconds",
    )


def get_controller(serial: Optional[str] = None) -> ADBController:
    return ADBController(serial=serial)


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/devices")
async def devices():
    device_list = await list_devices()
    return {"devices": [{"serial": serial, "status": status} for serial, status in device_list]}


@app.post("/api/tap")
async def tap(body: TapRequest):
    controller = get_controller(body.serial)
    await controller.tap(body.x, body.y)
    return {"status": "ok"}


@app.post("/api/swipe")
async def swipe(body: SwipeRequest):
    controller = get_controller(body.serial)
    await controller.swipe(body.start_x, body.start_y, body.end_x, body.end_y, body.duration_ms)
    return {"status": "ok"}


@app.post("/api/key")
async def key_event(body: KeyRequest):
    controller = get_controller(body.serial)
    await controller.send_key(body.key)
    return {"status": "ok"}


@app.post("/api/text")
async def send_text(body: TextRequest):
    controller = get_controller(body.serial)
    await controller.text(body.text)
    return {"status": "ok"}


@app.get("/stream")
async def stream(
    serial: Optional[str] = Query(default=None),
    interval: float = Query(default=0.6, ge=0.2, le=5.0),
):
    controller = get_controller(serial)
    stream = mjpeg_stream(controller, interval=interval)
    media_type = "multipart/x-mixed-replace; boundary=frame"
    return StreamingResponse(stream, media_type=media_type)


@app.post("/api/shell")
async def run_shell(body: ShellRequest):
    command = body.command.strip()
    if not command:
        raise HTTPException(status_code=400, detail="Command may not be empty")
    controller = get_controller(body.serial)
    try:
        result = await controller.run_shell(command)
    except ADBError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"output": result.decode("utf-8", errors="ignore")}


@app.post("/api/tcpip")
async def enable_tcpip(body: TcpipRequest):
    controller = get_controller(body.serial)
    try:
        message = await controller.enable_tcpip(body.port)
    except ADBError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"status": "ok", "message": message}


@app.post("/api/connect")
async def connect(body: ConnectRequest):
    try:
        message = await adb_connect(body.target, timeout=body.timeout)
    except ADBError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"status": "ok", "message": message, "stdout": message}


@app.post("/api/disconnect")
async def disconnect(body: DisconnectRequest):
    try:
        message = await adb_disconnect(body.target)
    except ADBError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"status": "ok", "message": message, "stdout": message}


@app.post("/api/debug/adb")
async def debug_adb(body: DebugADBRequest):
    try:
        args = shlex.split(body.command)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"无法解析命令: {exc}") from exc
    if not args:
        raise HTTPException(status_code=400, detail="请至少输入一个 adb 参数")
    result = await adb_raw(args, serial=body.serial, timeout=body.timeout)
    return result


@app.get("/api/screenshot")
async def screenshot(serial: Optional[str] = Query(default=None)):
    controller = get_controller(serial)
    try:
        png_bytes = await controller.screencap()
    except ADBError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    headers = {"Content-Disposition": f'attachment; filename="screenphantom-{timestamp}.png"'}
    return Response(content=png_bytes, media_type="image/png", headers=headers)


def create_app() -> FastAPI:
    """Factory for ASGI servers."""
    return app
