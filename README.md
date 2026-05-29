# ScreenPhantom

通过 ADB 在安卓 16+ 设备上远程查看并控制屏幕损坏的手机。

## 功能概览

- 指导用户将目标手机通过 USB/OTG 连接并启用调试模式。
- 提供基于 FastAPI 的本地服务，负责实时拉取屏幕画面、模拟触摸、模拟按键以及文本输入。
- 提供浏览器前端界面，可在另一台设备上查看画面并直接点击、拖动进行操作。

## 环境准备

1. 安装 [Android Platform Tools](https://developer.android.com/studio/releases/platform-tools) 并确认 `adb` 已添加到环境变量。
2. 安装 Python 3.10+。
3. 克隆或下载本项目：
   ```bash
   git clone <repo>
   cd ScreenPhantom
   ```
4. 安装依赖：
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows 使用 .venv\Scripts\activate
   pip install -r requirements.txt
   ```
   > 提示：运行命令前请设置 `PYTHONPATH=src`（Windows 可执行 `set PYTHONPATH=%CD%\\src`）。

### 在安卓主控端部署（Termux 示例）

若希望在一台安卓手机上运行 ScreenPhantom 来无线控制另一台设备，可按以下步骤：

1. 在主控手机上安装 [Termux](https://termux.dev/)。
2. 在 Termux 中安装依赖：
   ```bash
   pkg update
   pkg install python git android-tools
   python -m pip install --upgrade pip
   ```
3. 获取代码并安装依赖：
   ```bash
   git clone <repo>
   cd ScreenPhantom
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   export PYTHONPATH=$PWD/src
   ```
4. Termux 已包含 `adb`（android-tools）；如果想使用系统自带 ADB，可在启动前设置 `export ADB_PATH=/system/bin/adb`。

之后便可在 Termux 里启动 `python -m screenphantom`，再用同一手机的浏览器访问 `http://127.0.0.1:8000` 控制其他设备。

### 在局域网服务器部署

若希望在一台长期在线的 Linux 设备上集中运行后端，通过同一局域网的浏览器访问，可参考 [docs/lan_server_setup.md](docs/lan_server_setup.md)。该文档包含依赖安装、无线 ADB 常驻、以及可选的 `systemd` 服务示例。

## 连接阶段（启用 USB 调试）

1. **准备 OTG 键鼠**：如果目标手机屏幕无显示或触控失效，使用 OTG 连接鼠标（可选同时连接键盘）。
2. **开启 USB 调试**：
   - 进入 `设置 -> 关于手机 -> 版本号`，连续点击成为开发者。
   - 退回 `设置 -> 系统 -> 开发者选项`，开启「USB 调试」以及（若需要无线连接）「通过网络调试」。
3. **确认连接**：
   - 使用数据线将目标手机连接到控制端电脑。
   - 在电脑终端执行：
     ```bash
     adb devices
     ```
   - 第一次连接需要在手机上确认调试授权。屏幕损坏时可借助外接显示器、TalkBack 语音或语音助手确认。
4. **无线调试（可选）**：
   - 若需无线连接，保持手机与电脑同一局域网。
   - 执行 `adb tcpip 5555` 将设备切换为无线模式。
   - 记录手机在开发者选项中显示的 IP 与端口，执行 `adb connect <IP>:5555`。

> 如果设备未开启调试且无法通过屏幕操作，可使用制造商提供的备份工具、ADB 授权线或服务网点协助开启。

## 远程控制阶段

1. 启动服务：
   ```bash
   PYTHONPATH=src python -m screenphantom --host 0.0.0.0 --port 8000
   ```
2. 在浏览器打开 `http://<控制端IP>:8000`。
3. 在页面左上角点击「刷新」获取可用设备；若只连接一台可保持默认空值。
4. 浏览器中实时显示手机画面，支持：
   - 单击图像模拟点击。
   - 拖动图像触发滑动手势（按照拖动轨迹和时间计算时长）。
   - 顶部常用按键（Home/Back/电源/音量等）。
   - 输入框发送文本内容。
   - 发送自定义 shell 命令（可扩展）。

所有触控操作通过 `adb shell input ...` 指令完成，画面使用 `adb exec-out screencap -p` 周期性抓取并以 MJPEG 推送。

## 无线调试工作流

在页面的「无线 ADB」区域，可以完成以下操作：

- **无线连接**：填写被控手机的 IP 和端口（默认 5555），点击“连接”即调用 `adb connect`。成功后会自动刷新设备列表。
- **断开连接**：可针对当前地址或一键断开所有无线会话。
- **切换到 TCP/IP 模式**：选中已通过 USB 连线的设备后，填写端口并点击 `adb tcpip`，工具会在后台执行 `adb tcpip <port>`。对于已 root 的设备，可在确认 USB 调试授权后直接切换到无线模式。

被控设备已经 root 时，还可以直接调用 `/api/shell` 接口发送诸如 `setprop service.adb.tcp.port 5555 && stop adbd && start adbd` 的命令，以获得更稳定的无线调试服务。

## 界面与反馈

- 后端：`FastAPI` 提供 REST 接口与 MJPEG 流 `/stream`，当前默认帧率约 1.5 FPS（可通过 `interval` 参数适当调节）。
- 前端：原生 JavaScript 捕捉浏览器指针事件，根据图像实际尺寸进行坐标映射，同时绘制手势轨迹反馈。
- 如需高帧率，可将 `streamer.py` 换成基于 `adb exec-out screenrecord` + `ffmpeg` 管线或集成 `scrcpy` 库。

## 常见问题

- **画面刷新慢**：`screencap` 受限于 USB 传输，可在低分辨率设备上适当减小窗口尺寸或降低刷新频率。
- **ADB 掉线**：检查数据线质量，必要时改为无线调试；可在页面中重新刷新设备。
- **多设备冲突**：为特定操作提供 `serial` 参数或在页面下拉框中选择目标设备。

## 后续扩展方向

1. 集成 `scrcpy` 或 `minicap` 提升帧率与延迟表现。
2. 增加录屏、截图、文件传输等辅助功能。
3. 加入用户认证以及 HTTPS 以支持远程部署。
4. 基于 `adb shell sendevent` 实现更细粒度的输入控制。

现在即可启动 ScreenPhantom，在屏幕损坏的情况下远程操作高版本安卓设备。祝开发顺利！

## 打包为安卓 APK

仓库下的 `android/` 目录提供了纯 Kotlin 的宿主应用：启动后会把随应用打包的 `adb` 拷贝到内部目录，通过 `NanoHTTPD` 启动一个本地 HTTP 服务（端口 8080），然后在全屏 WebView 中加载同样的网页界面。

### 准备工作

1. 安装 Android Studio（推荐）或单独的 Android SDK 与 Gradle 8.x。
2. 在 `android/app/src/main/assets/adb/` 放入适用于主控手机架构的 `adb` 可执行文件，并确保文件名为 `adb`。可直接复制平台工具包中对应架构的二进制（arm64/armeabi-v7a）。
3. Android 13+ 需要自行启用“允许安装未知来源应用”。

### 构建步骤

```bash
cd android
# 若仓库内尚未生成 Gradle Wrapper，可在本机执行 `gradle wrapper --gradle-version 8.6`
./gradlew assembleDebug   # 生成 debug APK
# 或在 Android Studio 中选择 Build > Make Project / Build APK
```

生成的 APK 位于 `android/app/build/outputs/apk/debug/app-debug.apk`。首次启动时会自动把 `adb` 拷贝到应用内部目录、启动本地 HTTP 服务，并在 WebView 中访问 `http://127.0.0.1:8080`，界面与桌面版本一致。

### 运行提示

- 如果没有放置 `adb` 可执行文件，应用会提示服务启动失败。
- 建议在已 root 的主控手机上运行，以便 `adb` 有足够权限与无线调试设备通讯。
