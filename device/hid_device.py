# HID device classes for keyboard and mouse
# Uses MicroPython's usb.device.hid module (usb-device-hid package)

import time
from micropython import const
from usb.device.hid import HIDInterface

# ── Keyboard HID Report Descriptor ──────────────────────────────────────────
# Standard boot keyboard: 8-byte reports
# Byte 0: modifier bits, Byte 1: reserved, Bytes 2-7: up to 6 keycodes
_KEYBOARD_REPORT_DESC = bytes([
    0x05, 0x01,        # Usage Page (Generic Desktop)
    0x09, 0x06,        # Usage (Keyboard)
    0xA1, 0x01,        # Collection (Application)
    # Modifier keys (8 bits)
    0x05, 0x07,        #   Usage Page (Keyboard/Keypad)
    0x19, 0xE0,        #   Usage Minimum (Left Control)
    0x29, 0xE7,        #   Usage Maximum (Right GUI)
    0x15, 0x00,        #   Logical Minimum (0)
    0x25, 0x01,        #   Logical Maximum (1)
    0x75, 0x01,        #   Report Size (1)
    0x95, 0x08,        #   Report Count (8)
    0x81, 0x02,        #   Input (Data, Variable, Absolute)
    # Reserved byte
    0x75, 0x08,        #   Report Size (8)
    0x95, 0x01,        #   Report Count (1)
    0x81, 0x01,        #   Input (Constant)
    # LED output report (5 bits + 3 padding)
    0x05, 0x08,        #   Usage Page (LEDs)
    0x19, 0x01,        #   Usage Minimum (Num Lock)
    0x29, 0x05,        #   Usage Maximum (Kana)
    0x75, 0x01,        #   Report Size (1)
    0x95, 0x05,        #   Report Count (5)
    0x91, 0x02,        #   Output (Data, Variable, Absolute)
    0x75, 0x03,        #   Report Size (3)
    0x95, 0x01,        #   Report Count (1)
    0x91, 0x01,        #   Output (Constant)
    # Key arrays (6 keys)
    0x05, 0x07,        #   Usage Page (Keyboard/Keypad)
    0x19, 0x00,        #   Usage Minimum (0)
    0x29, 0x65,        #   Usage Maximum (101)
    0x15, 0x00,        #   Logical Minimum (0)
    0x25, 0x65,        #   Logical Maximum (101)
    0x75, 0x08,        #   Report Size (8)
    0x95, 0x06,        #   Report Count (6)
    0x81, 0x00,        #   Input (Data, Array)
    0xC0,              # End Collection
])

# ── Mouse HID Report Descriptor ─────────────────────────────────────────────
# 4-byte reports: buttons, dx, dy, scroll
_MOUSE_REPORT_DESC = bytes([
    0x05, 0x01,        # Usage Page (Generic Desktop)
    0x09, 0x02,        # Usage (Mouse)
    0xA1, 0x01,        # Collection (Application)
    0x09, 0x01,        #   Usage (Pointer)
    0xA1, 0x00,        #   Collection (Physical)
    # Buttons (3 bits + 5 padding)
    0x05, 0x09,        #     Usage Page (Button)
    0x19, 0x01,        #     Usage Minimum (Button 1)
    0x29, 0x03,        #     Usage Maximum (Button 3)
    0x15, 0x00,        #     Logical Minimum (0)
    0x25, 0x01,        #     Logical Maximum (1)
    0x75, 0x01,        #     Report Size (1)
    0x95, 0x03,        #     Report Count (3)
    0x81, 0x02,        #     Input (Data, Variable, Absolute)
    0x75, 0x05,        #     Report Size (5)
    0x95, 0x01,        #     Report Count (1)
    0x81, 0x01,        #     Input (Constant)
    # X, Y movement (-127 to +127)
    0x05, 0x01,        #     Usage Page (Generic Desktop)
    0x09, 0x30,        #     Usage (X)
    0x09, 0x31,        #     Usage (Y)
    0x15, 0x81,        #     Logical Minimum (-127)
    0x25, 0x7F,        #     Logical Maximum (127)
    0x75, 0x08,        #     Report Size (8)
    0x95, 0x02,        #     Report Count (2)
    0x81, 0x06,        #     Input (Data, Variable, Relative)
    # Scroll wheel (-127 to +127)
    0x09, 0x38,        #     Usage (Wheel)
    0x15, 0x81,        #     Logical Minimum (-127)
    0x25, 0x7F,        #     Logical Maximum (127)
    0x75, 0x08,        #     Report Size (8)
    0x95, 0x01,        #     Report Count (1)
    0x81, 0x06,        #     Input (Data, Variable, Relative)
    0xC0,              #   End Collection
    0xC0,              # End Collection
])

_KEY_REPORT_LEN = const(8)
_MOUSE_REPORT_LEN = const(4)

# ── Absolute Mouse HID Report Descriptor ──────────────────────────────────────
# 5-byte reports: buttons (1 byte), X (16-bit LE), Y (16-bit LE)
# X and Y range 0–32767, absolute positioning (no OS pointer acceleration)
_ABS_MOUSE_REPORT_DESC = bytes([
    0x05, 0x01,        # Usage Page (Generic Desktop)
    0x09, 0x02,        # Usage (Mouse)
    0xA1, 0x01,        # Collection (Application)
    0x09, 0x01,        #   Usage (Pointer)
    0xA1, 0x00,        #   Collection (Physical)
    # Buttons (3 bits + 5 padding)
    0x05, 0x09,        #     Usage Page (Button)
    0x19, 0x01,        #     Usage Minimum (Button 1)
    0x29, 0x03,        #     Usage Maximum (Button 3)
    0x15, 0x00,        #     Logical Minimum (0)
    0x25, 0x01,        #     Logical Maximum (1)
    0x75, 0x01,        #     Report Size (1)
    0x95, 0x03,        #     Report Count (3)
    0x81, 0x02,        #     Input (Data, Variable, Absolute)
    0x75, 0x05,        #     Report Size (5)
    0x95, 0x01,        #     Report Count (1)
    0x81, 0x01,        #     Input (Constant)
    # X position (0 to 32767, 16-bit unsigned)
    0x05, 0x01,        #     Usage Page (Generic Desktop)
    0x09, 0x30,        #     Usage (X)
    0x15, 0x00,        #     Logical Minimum (0)
    0x26, 0xFF, 0x7F,  #     Logical Maximum (32767)
    0x75, 0x10,        #     Report Size (16)
    0x95, 0x01,        #     Report Count (1)
    0x81, 0x02,        #     Input (Data, Variable, Absolute)
    # Y position (0 to 32767, 16-bit unsigned)
    0x09, 0x31,        #     Usage (Y)
    0x15, 0x00,        #     Logical Minimum (0)
    0x26, 0xFF, 0x7F,  #     Logical Maximum (32767)
    0x75, 0x10,        #     Report Size (16)
    0x95, 0x01,        #     Report Count (1)
    0x81, 0x02,        #     Input (Data, Variable, Absolute)
    0xC0,              #   End Collection
    0xC0,              # End Collection
])

_ABS_MOUSE_REPORT_LEN = const(5)


class KeyboardHID(HIDInterface):
    """USB HID Keyboard with boot protocol support."""

    def __init__(self):
        super().__init__(
            _KEYBOARD_REPORT_DESC,
            set_report_buf=bytearray(1),  # LED output report
            protocol=1,  # 1 = Keyboard boot protocol
            interface_str="Pico Keyboard",
        )
        self._report = bytearray(_KEY_REPORT_LEN)
        # Track currently held keys: modifier byte + up to 6 keycodes
        self._modifiers = 0
        self._keys = []  # list of held keycodes (max 6)

    def _build_report(self):
        """Build the 8-byte keyboard report from current state."""
        r = self._report
        r[0] = self._modifiers
        r[1] = 0  # reserved
        for i in range(6):
            r[2 + i] = self._keys[i] if i < len(self._keys) else 0
        return r

    def _send(self):
        """Send the current keyboard state as a HID report."""
        self.send_report(self._build_report())
        time.sleep_ms(2)

    def press_key(self, mod, code):
        """Press and release a key (with optional modifier)."""
        old_mod = self._modifiers
        self._modifiers |= mod
        if code and code not in self._keys:
            if len(self._keys) < 6:
                self._keys.append(code)
        self._send()
        # Release
        self._modifiers = old_mod
        if code and code in self._keys:
            self._keys.remove(code)
        self._send()

    def key_down(self, mod, code):
        """Hold a key down."""
        self._modifiers |= mod
        if code and code not in self._keys:
            if len(self._keys) < 6:
                self._keys.append(code)
        self._send()

    def key_up(self, mod, code):
        """Release a key."""
        self._modifiers &= ~mod
        if code and code in self._keys:
            self._keys.remove(code)
        self._send()

    def mod_key(self, mod_bits, code):
        """Press modifier combo + key, then release all."""
        self._modifiers |= mod_bits
        if code and code not in self._keys:
            if len(self._keys) < 6:
                self._keys.append(code)
        self._send()
        # Release
        self._modifiers &= ~mod_bits
        if code and code in self._keys:
            self._keys.remove(code)
        self._send()

    def type_chars(self, chars):
        """Type a sequence of (mod, keycode) pairs with proper release between."""
        prev_code = None
        for mod, code in chars:
            # If same key repeated, need to release first so host sees distinct presses
            if code == prev_code:
                self._modifiers = 0
                if code in self._keys:
                    self._keys.remove(code)
                self._send()
            # Press
            self._modifiers = mod
            self._keys = [code] if code else []
            self._send()
            prev_code = code
        # Release all
        self._modifiers = 0
        self._keys = []
        self._send()

    def release_all(self):
        """Release all keys and modifiers."""
        self._modifiers = 0
        self._keys = []
        self._send()


class MouseHID(HIDInterface):
    """USB HID Mouse with 3 buttons and scroll wheel."""

    def __init__(self):
        super().__init__(
            _MOUSE_REPORT_DESC,
            set_report_buf=bytearray(0),
            protocol=2,  # 2 = Mouse boot protocol
            interface_str="Pico Mouse",
        )
        self._report = bytearray(_MOUSE_REPORT_LEN)
        self._buttons = 0  # button state bitmask

    def _to_signed(self, val):
        """Clamp and convert to signed byte."""
        val = max(-127, min(127, val))
        return val & 0xFF

    def _send(self, buttons, dx, dy, scroll):
        r = self._report
        r[0] = buttons
        r[1] = self._to_signed(dx)
        r[2] = self._to_signed(dy)
        r[3] = self._to_signed(scroll)
        self.send_report(r)
        time.sleep_ms(2)

    def move(self, dx, dy):
        """Move mouse by (dx, dy), automatically chunking large values."""
        while dx != 0 or dy != 0:
            chunk_x = max(-127, min(127, dx))
            chunk_y = max(-127, min(127, dy))
            self._send(self._buttons, chunk_x, chunk_y, 0)
            dx -= chunk_x
            dy -= chunk_y

    def click(self, button_bit):
        """Click (press + release) a mouse button."""
        self._buttons |= button_bit
        self._send(self._buttons, 0, 0, 0)
        self._buttons &= ~button_bit
        self._send(self._buttons, 0, 0, 0)

    def button_down(self, button_bit):
        """Press a mouse button."""
        self._buttons |= button_bit
        self._send(self._buttons, 0, 0, 0)

    def button_up(self, button_bit):
        """Release a mouse button."""
        self._buttons &= ~button_bit
        self._send(self._buttons, 0, 0, 0)

    def scroll(self, amount):
        """Scroll by amount (positive=up), chunking as needed."""
        while amount != 0:
            chunk = max(-127, min(127, amount))
            self._send(self._buttons, 0, 0, chunk)
            amount -= chunk

    def release_all(self):
        """Release all buttons."""
        self._buttons = 0
        self._send(0, 0, 0, 0)


class AbsMouseHID(HIDInterface):
    """USB HID Absolute Mouse — positions cursor via absolute coordinates (0–32767)."""

    def __init__(self):
        super().__init__(
            _ABS_MOUSE_REPORT_DESC,
            set_report_buf=bytearray(0),
            protocol=0,  # No boot protocol for absolute mouse
            interface_str="Pico Abs Mouse",
        )
        self._report = bytearray(_ABS_MOUSE_REPORT_LEN)
        self._buttons = 0

    def _send(self, buttons, x, y):
        r = self._report
        r[0] = buttons
        r[1] = x & 0xFF
        r[2] = (x >> 8) & 0xFF
        r[3] = y & 0xFF
        r[4] = (y >> 8) & 0xFF
        self.send_report(r)
        time.sleep_ms(2)

    def move_abs(self, x, y):
        """Move cursor to absolute position (0–32767 range)."""
        x = max(0, min(32767, x))
        y = max(0, min(32767, y))
        self._send(self._buttons, x, y)

    def release_all(self):
        """Release all buttons."""
        self._buttons = 0
        self._send(0, 0, 0)
