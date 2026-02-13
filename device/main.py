# main.py — Command loop for USB HID keyboard+mouse
# Reads newline-terminated ASCII commands from CDC serial,
# dispatches to keyboard/mouse HID devices.

import sys
import time
import select
import machine
import micropython

from boot import keyboard, mouse, abs_mouse
from protocol import parse, Command


def _respond(msg):
    """Write a response line to serial output."""
    sys.stdout.write(msg + "\n")


def _dispatch(cmd):
    """Execute a parsed command."""
    k = cmd.kind
    p = cmd.params

    # System
    if k == "ping":
        _respond("PONG")
        return
    if k == "reset":
        keyboard.release_all()
        mouse.release_all()
        _respond("OK")
        return
    if k == "releaseall":
        keyboard.release_all()
        _respond("OK")
        return
    if k == "bootloader":
        _respond("OK")
        time.sleep(0.1)
        machine.bootloader()
        return

    # Keyboard
    if k == "key":
        keyboard.press_key(p["mod"], p["code"])
        _respond("OK")
        return
    if k == "keydown":
        keyboard.key_down(p["mod"], p["code"])
        _respond("OK")
        return
    if k == "keyup":
        keyboard.key_up(p["mod"], p["code"])
        _respond("OK")
        return
    if k == "mod":
        keyboard.mod_key(p["mod"], p["code"])
        _respond("OK")
        return
    if k == "type":
        keyboard.type_chars(p["chars"])
        _respond("OK")
        return

    # Mouse
    if k == "mouse_abs":
        abs_mouse.move_abs(p["x"], p["y"])
        _respond("OK")
        return
    if k == "mouse_move":
        mouse.move(p["dx"], p["dy"])
        _respond("OK")
        return
    if k == "mouse_click":
        mouse.click(p["button"])
        _respond("OK")
        return
    if k == "mouse_down":
        mouse.button_down(p["button"])
        _respond("OK")
        return
    if k == "mouse_up":
        mouse.button_up(p["button"])
        _respond("OK")
        return
    if k == "mouse_scroll":
        mouse.scroll(p["amount"])
        _respond("OK")
        return

    _respond("ERR unknown command kind")


def main():
    # Safety delay — gives mpremote a window to connect before we take over stdin
    time.sleep(2)

    # Disable Ctrl-C interception so raw bytes pass through
    micropython.kbd_intr(-1)

    poller = select.poll()
    poller.register(sys.stdin.buffer, select.POLLIN)

    buf = bytearray()

    while True:
        # Non-blocking poll with 10ms timeout
        events = poller.poll(10)
        if events:
            data = sys.stdin.buffer.read(1)
            if data:
                b = data[0]
                if b == 0x0A:  # newline
                    try:
                        line = buf.decode("utf-8")
                    except Exception:
                        _respond("ERR invalid utf-8")
                        buf = bytearray()
                        continue
                    buf = bytearray()

                    if not line.strip():
                        continue

                    result = parse(line)
                    if isinstance(result, str):
                        _respond("ERR " + result)
                    else:
                        try:
                            _dispatch(result)
                        except Exception as e:
                            _respond("ERR " + str(e))
                elif b == 0x0D:  # ignore CR
                    pass
                else:
                    buf.append(b)
        else:
            # No data — yield
            time.sleep_ms(1)


main()
