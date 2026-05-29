# ScreenPhantom

Web-based Android remote control via ADB. View and interact with your phone screen from any browser — designed to integrate seamlessly with Home Assistant.

## ✨ Features

- **Real-time screen mirroring** — MJPEG stream at ~5 FPS, optimized for low bandwidth
- **Touch control** — Tap and swipe directly on the browser canvas
- **Multi-device** — Connect, disconnect, and switch between multiple Android devices
- **Hardware buttons** — Power, Home, Back, Recents, Volume
- **Text injection** — Type on your phone from the browser
- **Wireless ADB** — Connect devices over WiFi, no USB needed
- **Mobile-first UI** — Responsive design, works great on phones and tablets
- **Home Assistant ready** — Embed as iframe panel, toggle on/off via HA automation

## 🏠 Home Assistant Integration

ScreenPhantom is designed to be a **smart home panel** — not just a standalone tool.

### How it works with HA

1. **On-demand service** — A toggle switch in HA starts/stops ScreenPhantom to save resources
2. **Embedded iframe** — The web UI lives inside an HA dashboard tab
3. **Zero-touch operation** — Tap a button on your HA app → service starts → screen appears

### Setup in HA

Add to `configuration.yaml`:

```yaml
shell_command:
  screenphantom_start: "ssh -i /config/.ssh/id_rsa root@<server-ip> bash /root/screenphantom_ctl.sh start"
  screenphantom_stop: "ssh -i /config/.ssh/id_rsa root@<server-ip> bash /root/screenphantom_ctl.sh stop"

input_boolean:
  screenphantom:
    name: ScreenPhantom
    icon: mdi:cellphone-link
```

Add automations:

```yaml
- alias: ScreenPhantom On
  trigger:
    - platform: state
      entity_id: input_boolean.screenphantom
      to: "on"
  action:
    - service: shell_command.screenphantom_start

- alias: ScreenPhantom Off
  trigger:
    - platform: state
      entity_id: input_boolean.screenphantom
      to: "off"
  action:
    - service: shell_command.screenphantom_stop
```

Add an iframe card in your Lovelace dashboard:

```yaml
type: iframe
url: "http://<server-ip>:8000"
aspect_ratio: "1:2"
```

Now you can control any Android device from your smart home dashboard — start the service only when needed, mirror the screen, tap buttons, all from one place.

## 🚀 Quick Start

```bash
git clone https://github.com/tangshui9527/ScreenPhantom.git
cd ScreenPhantom
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=src python3 -m screenphantom --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000` and connect your device.

## 📱 Connect Devices

```bash
adb connect <phone-ip>:5555
```

Or use the built-in connect UI in the web interface.

## 🔧 Control Script

```bash
./screenphantom_ctl.sh start   # Start service
./screenphantom_ctl.sh stop    # Stop service  
./screenphantom_ctl.sh status  # Check if running
```

## Architecture

```
Browser ←→ FastAPI (uvicorn)
              ├── GET /stream?serial=xxx  → adb screencap → PIL resize → JPEG MJPEG
              ├── POST /api/tap           → adb shell input tap
              ├── POST /api/swipe         → adb shell input swipe
              ├── POST /api/key           → adb shell input keyevent
              ├── POST /api/text          → adb shell input text
              ├── POST /api/connect       → adb connect
              ├── POST /api/disconnect    → adb disconnect
              └── GET /api/devices        → adb devices
```

## Requirements

- Python 3.10+
- `adb` in PATH
- Pillow, FastAPI, Uvicorn, Jinja2

## License

MIT
