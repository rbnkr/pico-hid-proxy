# boot.py — Runs at power-on before main.py
# Initializes USB composite device: CDC (serial) + HID Keyboard + HID Mouse

import usb.device
from hid_device import KeyboardHID, MouseHID, AbsMouseHID

# Create HID interface instances (stored as module globals for main.py to import)
keyboard = KeyboardHID()
mouse = MouseHID()
abs_mouse = AbsMouseHID()

# Initialize USB device with all HID interfaces + builtin CDC/REPL driver
usb.device.get().init(keyboard, mouse, abs_mouse, builtin_driver=True)
