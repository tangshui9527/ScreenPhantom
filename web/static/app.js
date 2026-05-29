(() => {
  const deviceSelect = document.getElementById("device-select");
  const refreshButton = document.getElementById("refresh-devices");
  const deviceControls = document.querySelector(".device-controls");
  const textForm = document.getElementById("text-form");
  const textInput = document.getElementById("text-input");
  const screenImg = document.getElementById("screen");
  const canvas = document.getElementById("input-layer");
  const ctx = canvas.getContext("2d");
  const connectForm = document.getElementById("connect-form");
  const hostInput = document.getElementById("adb-host");
  const portInput = document.getElementById("adb-port");
  const disconnectTargetBtn = document.getElementById("disconnect-target");
  const screenshotButton = document.getElementById("capture-screenshot");
  const deviceStatus = document.getElementById("device-status");
  const connectionStatus = document.getElementById("connection-status");

  const state = { pointer: null, deviceSerial: null };

  function getSelectedSerial() {
    state.deviceSerial = deviceSelect.value || null;
    return state.deviceSerial;
  }

  function updateStatus(msg, type = "info") {
    if (!connectionStatus) return;
    connectionStatus.textContent = msg;
    connectionStatus.className = "connection-status";
    if (type === "error") connectionStatus.classList.add("error");
    else if (type === "warning") connectionStatus.classList.add("warning");
  }

  function updateDeviceStatus() {
    if (!deviceStatus) return;
    if (state.deviceSerial) {
      deviceStatus.textContent = state.deviceSerial;
      deviceStatus.style.color = "#22c55e";
    } else {
      deviceStatus.textContent = "No device";
      deviceStatus.style.color = "#94a3b8";
    }
  }

  async function apiPost(path, payload = {}) {
    const res = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json().catch(() => null);
    if (!res.ok) throw new Error(data?.detail || res.statusText);
    return data || {};
  }

  async function refreshDevices() {
    updateStatus("Scanning...", "warning");
    try {
      const res = await fetch("/api/devices");
      const data = await res.json();
      const prev = state.deviceSerial;
      deviceSelect.innerHTML = "";
      data.devices.forEach((d) => {
        const opt = document.createElement("option");
        opt.value = d.serial;
        opt.textContent = `${d.serial} [${d.status}]`;
        if (d.serial === prev) opt.selected = true;
        deviceSelect.appendChild(opt);
      });
      // Auto-select first if nothing selected
      if (!deviceSelect.value && data.devices.length > 0) {
        deviceSelect.value = data.devices[0].serial;
      }
      onDeviceChange();
      updateStatus(data.devices.length + " device(s)", "info");
    } catch (e) {
      updateStatus("Scan failed", "error");
    }
  }

  function onDeviceChange() {
    const serial = getSelectedSerial();
    updateDeviceStatus();
    if (serial) {
      screenImg.src = "/stream?serial=" + encodeURIComponent(serial) + "&interval=0.2";
    } else {
      screenImg.src = "";
    }
  }

  async function handleConnect(e) {
    e.preventDefault();
    const host = hostInput.value.trim();
    const port = portInput.value.trim() || "5555";
    if (!host) return;
    const target = `${host}:${port}`;
    updateStatus("Connecting " + target + "...", "warning");
    try {
      await apiPost("/api/connect", { target });
      updateStatus("Connected", "info");
      await refreshDevices();
    } catch (err) {
      updateStatus("Failed: " + err.message, "error");
    }
  }

  async function handleDisconnect() {
    const serial = getSelectedSerial();
    if (!serial) { updateStatus("Select a device first", "warning"); return; }
    updateStatus("Disconnecting " + serial + "...", "warning");
    try {
      await apiPost("/api/disconnect", { target: serial });
      screenImg.src = "";
      updateStatus("Disconnected", "info");
      await refreshDevices();
    } catch (err) {
      updateStatus("Failed: " + err.message, "error");
    }
  }

  // Touch/pointer handling
  function resizeCanvas() {
    const r = screenImg.getBoundingClientRect();
    canvas.width = r.width;
    canvas.height = r.height;
  }

  function toDevice(cx, cy) {
    const r = canvas.getBoundingClientRect();
    if (!screenImg.naturalWidth) return null;
    return {
      x: Math.round((cx - r.left) * screenImg.naturalWidth / r.width),
      y: Math.round((cy - r.top) * screenImg.naturalHeight / r.height),
    };
  }

  function onPointerDown(e) {
    const c = toDevice(e.clientX, e.clientY);
    if (!c) return;
    const r = canvas.getBoundingClientRect();
    state.pointer = { start: c, startLocal: { x: e.clientX - r.left, y: e.clientY - r.top }, time: e.timeStamp };
    canvas.setPointerCapture(e.pointerId);
  }

  function onPointerMove(e) {
    if (!state.pointer) return;
    const r = canvas.getBoundingClientRect();
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.strokeStyle = "rgba(99,102,241,0.7)";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(state.pointer.startLocal.x, state.pointer.startLocal.y);
    ctx.lineTo(e.clientX - r.left, e.clientY - r.top);
    ctx.stroke();
  }

  async function onPointerUp(e) {
    if (!state.pointer) return;
    canvas.releasePointerCapture(e.pointerId);
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const start = state.pointer.start;
    const end = toDevice(e.clientX, e.clientY) || start;
    const elapsed = e.timeStamp - state.pointer.time;
    state.pointer = null;
    const serial = getSelectedSerial();
    const dist = Math.hypot(end.x - start.x, end.y - start.y);
    try {
      if (dist < 25) {
        await apiPost("/api/tap", { x: start.x, y: start.y, serial });
      } else {
        const dur = Math.max(150, Math.min(1000, Math.round(elapsed)));
        await apiPost("/api/swipe", { x1: start.x, y1: start.y, x2: end.x, y2: end.y, duration_ms: dur, serial });
      }
    } catch (err) {
      updateStatus("Touch failed", "error");
    }
  }

  async function handleKey(e) {
    const btn = e.target.closest("[data-key]");
    if (!btn) return;
    const key = btn.dataset.key;
    try {
      await apiPost("/api/key", { key, serial: getSelectedSerial() });
      updateStatus("Sent " + key.replace("KEYCODE_", ""), "info");
    } catch (err) {
      updateStatus("Key failed", "error");
    }
  }

  async function handleText(e) {
    e.preventDefault();
    if (!textInput.value) return;
    try {
      await apiPost("/api/text", { text: textInput.value, serial: getSelectedSerial() });
      textInput.value = "";
    } catch (err) {
      updateStatus("Text failed", "error");
    }
  }

  async function handleScreenshot() {
    const serial = getSelectedSerial();
    let url = "/api/screenshot";
    if (serial) url += "?serial=" + encodeURIComponent(serial);
    try {
      const res = await fetch(url);
      if (!res.ok) throw new Error("Failed");
      const blob = await res.blob();
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "screenshot-" + Date.now() + ".png";
      a.click();
      URL.revokeObjectURL(a.href);
      updateStatus("Screenshot saved", "info");
    } catch (err) {
      updateStatus("Screenshot failed", "error");
    }
  }

  // Events
  screenImg.addEventListener("load", resizeCanvas);
  window.addEventListener("resize", resizeCanvas);
  canvas.addEventListener("pointerdown", onPointerDown);
  canvas.addEventListener("pointermove", onPointerMove);
  canvas.addEventListener("pointerup", onPointerUp);
  canvas.addEventListener("pointercancel", onPointerUp);
  deviceSelect.addEventListener("change", onDeviceChange);
  refreshButton.addEventListener("click", refreshDevices);
  disconnectTargetBtn.addEventListener("click", handleDisconnect);
  connectForm.addEventListener("submit", handleConnect);
  if (deviceControls) deviceControls.addEventListener("click", handleKey);
  if (textForm) textForm.addEventListener("submit", handleText);
  if (screenshotButton) screenshotButton.addEventListener("click", handleScreenshot);

  // Init
  refreshDevices();
})();
