"""Fast screen streaming via screencap."""

from __future__ import annotations

import asyncio
import logging
from io import BytesIO
from typing import AsyncIterator

from .adb import ADBController, ADBError

try:
    from PIL import Image
except ImportError:
    Image = None

LOGGER = logging.getLogger(__name__)


async def mjpeg_stream(
    controller: ADBController,
    *,
    interval: float = 0.1,
    max_width: int = 360,
    jpeg_quality: int = 25,
) -> AsyncIterator[bytes]:
    """Yield MJPEG frames as fast as possible."""

    boundary = b"--frame"
    while True:
        try:
            raw = await controller.screencap()
            frame, ctype = _compress(raw, max_width, jpeg_quality)
            yield (
                boundary + b"\r\nContent-Type: " + ctype
                + b"\r\nContent-Length: " + str(len(frame)).encode()
                + b"\r\n\r\n" + frame + b"\r\n"
            )
        except ADBError:
            await asyncio.sleep(0.5)
            continue
        await asyncio.sleep(interval)


def _compress(png: bytes, max_w: int, quality: int) -> tuple[bytes, bytes]:
    if Image is None:
        return png, b"image/png"
    try:
        with Image.open(BytesIO(png)) as img:
            if img.mode != "RGB":
                img = img.convert("RGB")
            if img.width > max_w:
                r = max_w / img.width
                img = img.resize((max_w, int(img.height * r)), Image.Resampling.NEAREST)
            buf = BytesIO()
            img.save(buf, format="JPEG", quality=quality)
            return buf.getvalue(), b"image/jpeg"
    except Exception:
        pass
    return png, b"image/png"
