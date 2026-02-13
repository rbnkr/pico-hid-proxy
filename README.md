# Pico HID

A Raspberry Pi Pico 2 W acting as a USB HID keyboard and mouse, controlled over serial from a host PC.

## Project Structure

```
device/          MicroPython code that runs on the Pico (frozen into firmware)
host/            PC-side serial host script
firmware/        Built UF2 firmware output
input_monitor/   Windows tool to detect real vs emulated input
```

## Building Firmware

The device code is frozen into a custom MicroPython firmware, producing a single `.uf2` file. The build runs in Docker — no local toolchain needed.

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/)

### Build

```
./build_firmware.sh
```

This builds MicroPython v1.27.0 for `RPI_PICO2_W` with all `device/` code and the `usb-device-hid` library frozen in. Output: `firmware/pico_hid_firmware.uf2`.

The first build takes a few minutes (cloning MicroPython, compiling toolchain). Subsequent builds after code changes are fast thanks to Docker layer caching.

To force a clean rebuild:

```
./build_firmware.sh --clean
```

### Flash

1. Hold BOOTSEL on the Pico and plug it in (or send the `bootloader` command if already connected)
2. Copy `firmware/pico_hid_firmware.uf2` to the USB drive that appears

## Host Scripts

The host scripts run on your PC to communicate with the Pico over serial.

### Prerequisites

- Python 3.12+

Optionally create a conda environment:

```
conda create -n pico-hid python=3.12 -y
conda activate pico-hid
```

Install dependencies:

```
pip install -r requirements.txt
```

### Connect

```
python host/host.py          # auto-detect port
python host/host.py COM5     # manual port
```

Type `help` once connected for a list of commands.

## Commands

| Command | Description |
|---|---|
| `ping` | Test connection (returns PONG) |
| `key <name>` | Press and release a key |
| `keydown <name>` / `keyup <name>` | Hold / release a key |
| `mod <mods> <key>` | Modifier combo (e.g. `mod ctrl+shift esc`) |
| `type <text>` | Type a string |
| `releaseall` | Release all keys |
| `mouse move <dx> <dy>` | Relative mouse move |
| `mouse abs <x> <y>` | Absolute mouse move |
| `mouse click <btn>` | Click left/right/middle |
| `mouse down <btn>` / `mouse up <btn>` | Hold / release button |
| `mouse scroll <n>` | Scroll (positive = up) |
| `reset` | Release all keys and buttons |
| `bootloader` | Reboot Pico into BOOTSEL (UF2 flash) mode |

## Input Monitor

A separate Windows tool that uses low-level hooks (`WH_KEYBOARD_LL` / `WH_MOUSE_LL`) to detect whether keyboard and mouse events are real hardware input or emulated/injected. Checks the `LLKHF_INJECTED` and `LLMHF_INJECTED` flags set by the OS on synthetic input.

Run the monitor (requires native Windows Python, not WSL):

```
python input_monitor/main.py
```

Press Ctrl+C to stop the monitor.

## Licenses

This firmware is built for Raspberry Pi Pico 2 W and includes MicroPython (MIT), Pico SDK (BSD-3-Clause), TinyUSB (MIT), lwIP (BSD), cyw43-driver and BTstack (licensed by Raspberry Pi Ltd for use with Pico W hardware).
