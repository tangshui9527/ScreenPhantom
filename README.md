# ScreenPhantom

Web-based Android remote control via ADB. View and interact with your phone screen from any browser.

## Features

- Real-time MJPEG screen mirroring (low-latency, 360p)
- Touch control: tap and swipe via pointer events
- Multi-device support: connect/disconnect/switch devices
- Hardware buttons: Power, Home, Back, Recents, Volume
- Text input injection
- Wireless ADB connect/disconnect
- Mobile-friendly responsive UI
- Designed to embed in Home Assistant via iframe

## Quick Start

```bash
cd ScreenPhantom
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=src python3 -m screenphantom --host 0.0.0.0 --port 8000
```

Open `http://<server-ip>:8000` in browser.

## One-line Start

```bash
bash start.sh
```

## Control Script

```bash
/root/screenphantom_ctl.sh start   # start service
/root/screenphantom_ctl.sh stop    # stop service
/root/screenphantom_ctl.sh status  # check status
```

## Home Assistant Integration

Added as iframe panel in HA dashboard (Scrcpy tab).  
Toggle switch available in Media card to start/stop on demand.

## Architecture

- **Backend**: FastAPI + Uvicorn
- **Streaming**: `adb exec-out screencap -p` → PIL resize → JPEG MJPEG push
- **Frontend**: Vanilla JS, pointer events for touch, responsive CSS grid
- **ADB**: Wireless TCP/IP, multi-device with serial selection

## Requirements

- Python 3.10+
- adb in PATH
- Pillow (for JPEG compression)
- FastAPI, Uvicorn, Jinja2
