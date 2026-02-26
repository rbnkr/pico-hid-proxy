#!/usr/bin/env python3
"""Interactive host script for Pico HID device.

Usage:
    python host.py [COM_PORT]
    python host.py COM5
    python host.py /dev/ttyACM0

Commands are sent as-is to the Pico. Type 'quit' or 'exit' to close.
"""

import sys
import serial
import serial.tools.list_ports
import threading
import time


def find_pico_port():
    """Auto-detect the Pico's serial port."""
    ports = serial.tools.list_ports.comports()
    for p in ports:
        desc = (p.description or "").lower()
        vid = p.vid or 0
        # MicroPython on RP2040/RP2350 uses VID 0x2E8A
        if vid == 0x2E8A or "pico" in desc or "board in fs mode" in desc:
            return p.device
    # Fallback: show available ports
    if ports:
        print("Available ports:")
        for p in ports:
            print(f"  {p.device}  -  {p.description}")
    return None


def reader_thread(ser, stop_event):
    """Background thread that prints incoming data from the Pico."""
    while not stop_event.is_set():
        try:
            if ser.in_waiting > 0:
                line = ser.readline().decode("utf-8", errors="replace").rstrip()
                if line:
                    print(f"< {line}")
            else:
                time.sleep(0.01)
        except (serial.SerialException, OSError):
            if not stop_event.is_set():
                print("[disconnected]")
            break


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else find_pico_port()
    if not port:
        print("No Pico found. Specify port: python host.py COM5")
        sys.exit(1)

    print(f"Connecting to {port}...")
    try:
        ser = serial.Serial(port, timeout=0.1)
    except serial.SerialException as e:
        print(f"Failed to open {port}: {e}")
        sys.exit(1)

    print(f"Connected. Type commands (or 'help' for examples, 'quit' to exit).")
    print(f"NOTE: Keyboard commands (type/key) send HID keystrokes to the focused window.")
    print(f"      Focus a text editor when testing keyboard commands.\n")

    stop = threading.Event()
    t = threading.Thread(target=reader_thread, args=(ser, stop), daemon=True)
    t.start()

    try:
        while True:
            try:
                cmd = input("> ")
            except EOFError:
                break

            if cmd.strip().lower() in ("quit", "exit"):
                break

            if cmd.strip().lower() == "help":
                print("""
Keyboard:
  key <name>            - Press+release (e.g. key a, key enter)
  keydown <name>        - Hold key
  keyup <name>          - Release key
  mod <mods> <key>      - Modifier combo (e.g. mod ctrl+shift esc)
  type <text>           - Type string (e.g. type Hello World!)
  releaseall            - Release all keys

Mouse:
  mouse move <dx> <dy>  - Relative move (e.g. mouse move 100 -50)
  mouse abs <x> <y>     - Absolute move (e.g. mouse abs 500 300)
  mouse click <btn>     - Click (left/right/middle)
  mouse down <btn>      - Hold button
  mouse up <btn>        - Release button
  mouse scroll <n>      - Scroll (positive=up, e.g. mouse scroll -3)

WiFi:
  wifi set <ssid> <pw>  - Save WiFi credentials
  wifi get              - Show saved credentials
  wifi connect [s] [p]  - Connect (saves creds if given, uses saved if not)
  wifi disconnect       - Disconnect from WiFi
  wifi status           - Show connection status, IP, signal strength
  wifi clear            - Delete saved credentials and disconnect

API:
  api token <value>     - Set the API token for web access

System:
  ping                  - Test connection (expect PONG)
  reset                 - Release all keys + buttons
  bootloader            - Reboot Pico into BOOTSEL mode
  quit / exit           - Close this script
""")
                continue

            if not cmd.strip():
                continue

            # Keyboard commands type into the focused window — give user
            # time to Alt-Tab to a target window first.
            verb = cmd.strip().split()[0].lower()
            if verb in ("type", "key", "keydown", "mod", "mouse"):
                delay = 3
                for i in range(delay, 0, -1):
                    print(f"  Sending in {i}... (Alt-Tab to target window)", end="\r")
                    time.sleep(1)
                print(" " * 60, end="\r")  # clear countdown line

            ser.write((cmd + "\n").encode("utf-8"))

    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        ser.close()
        print("\nDisconnected.")


if __name__ == "__main__":
    main()
