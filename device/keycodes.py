# USB HID Keyboard Usage IDs and character mappings
# Reference: USB HID Usage Tables 1.12, Section 10 (Keyboard/Keypad Page 0x07)

# Modifier bit masks (byte 0 of keyboard report)
MOD_NONE = 0x00
MOD_LEFT_CTRL = 0x01
MOD_LEFT_SHIFT = 0x02
MOD_LEFT_ALT = 0x04
MOD_LEFT_GUI = 0x08
MOD_RIGHT_CTRL = 0x10
MOD_RIGHT_SHIFT = 0x20
MOD_RIGHT_ALT = 0x40
MOD_RIGHT_GUI = 0x80

# Friendly name -> modifier bit
MODIFIER_KEYS = {
    "ctrl": MOD_LEFT_CTRL,
    "lctrl": MOD_LEFT_CTRL,
    "rctrl": MOD_RIGHT_CTRL,
    "shift": MOD_LEFT_SHIFT,
    "lshift": MOD_LEFT_SHIFT,
    "rshift": MOD_RIGHT_SHIFT,
    "alt": MOD_LEFT_ALT,
    "lalt": MOD_LEFT_ALT,
    "ralt": MOD_RIGHT_ALT,
    "gui": MOD_LEFT_GUI,
    "lgui": MOD_LEFT_GUI,
    "rgui": MOD_RIGHT_GUI,
    "win": MOD_LEFT_GUI,
    "super": MOD_LEFT_GUI,
    "meta": MOD_LEFT_GUI,
    "cmd": MOD_LEFT_GUI,
    "option": MOD_LEFT_ALT,
}

# Key name -> USB HID usage ID
# Letters a-z = 0x04-0x1D, digits 1-9 = 0x1E-0x26, 0 = 0x27
KEYCODES = {
    # Letters
    "a": 0x04, "b": 0x05, "c": 0x06, "d": 0x07, "e": 0x08,
    "f": 0x09, "g": 0x0A, "h": 0x0B, "i": 0x0C, "j": 0x0D,
    "k": 0x0E, "l": 0x0F, "m": 0x10, "n": 0x11, "o": 0x12,
    "p": 0x13, "q": 0x14, "r": 0x15, "s": 0x16, "t": 0x17,
    "u": 0x18, "v": 0x19, "w": 0x1A, "x": 0x1B, "y": 0x1C,
    "z": 0x1D,
    # Digits
    "1": 0x1E, "2": 0x1F, "3": 0x20, "4": 0x21, "5": 0x22,
    "6": 0x23, "7": 0x24, "8": 0x25, "9": 0x26, "0": 0x27,
    # Control keys
    "enter": 0x28, "return": 0x28,
    "escape": 0x29, "esc": 0x29,
    "backspace": 0x2A, "bksp": 0x2A,
    "tab": 0x2B,
    "space": 0x2C, "spacebar": 0x2C,
    # Punctuation (US layout, unshifted)
    "minus": 0x2D, "-": 0x2D,
    "equal": 0x2E, "=": 0x2E,
    "leftbracket": 0x2F, "[": 0x2F,
    "rightbracket": 0x30, "]": 0x30,
    "backslash": 0x31, "\\": 0x31,
    "semicolon": 0x33, ";": 0x33,
    "quote": 0x34, "'": 0x34,
    "grave": 0x35, "`": 0x35,
    "comma": 0x36, ",": 0x36,
    "period": 0x37, ".": 0x37,
    "slash": 0x38, "/": 0x38,
    # Lock keys
    "capslock": 0x39,
    # Function keys
    "f1": 0x3A, "f2": 0x3B, "f3": 0x3C, "f4": 0x3D,
    "f5": 0x3E, "f6": 0x3F, "f7": 0x40, "f8": 0x41,
    "f9": 0x42, "f10": 0x43, "f11": 0x44, "f12": 0x45,
    # Navigation
    "printscreen": 0x46, "prtsc": 0x46,
    "scrolllock": 0x47,
    "pause": 0x48, "break": 0x48,
    "insert": 0x49, "ins": 0x49,
    "home": 0x4A,
    "pageup": 0x4B, "pgup": 0x4B,
    "delete": 0x4C, "del": 0x4C,
    "end": 0x4D,
    "pagedown": 0x4E, "pgdn": 0x4E,
    "right": 0x4F, "rightarrow": 0x4F,
    "left": 0x50, "leftarrow": 0x50,
    "down": 0x51, "downarrow": 0x51,
    "up": 0x52, "uparrow": 0x52,
    # Numpad
    "numlock": 0x53,
    "kp_divide": 0x54, "kp_multiply": 0x55,
    "kp_minus": 0x56, "kp_plus": 0x57,
    "kp_enter": 0x58,
    "kp_1": 0x59, "kp_2": 0x5A, "kp_3": 0x5B,
    "kp_4": 0x5C, "kp_5": 0x5D, "kp_6": 0x5E,
    "kp_7": 0x5F, "kp_8": 0x60, "kp_9": 0x61,
    "kp_0": 0x62, "kp_dot": 0x63,
    # Application key
    "menu": 0x65, "app": 0x65,
}

# Character -> (keycode, needs_shift)
# US QWERTY layout
CHAR_MAP = {
    "a": (0x04, False), "b": (0x05, False), "c": (0x06, False),
    "d": (0x07, False), "e": (0x08, False), "f": (0x09, False),
    "g": (0x0A, False), "h": (0x0B, False), "i": (0x0C, False),
    "j": (0x0D, False), "k": (0x0E, False), "l": (0x0F, False),
    "m": (0x10, False), "n": (0x11, False), "o": (0x12, False),
    "p": (0x13, False), "q": (0x14, False), "r": (0x15, False),
    "s": (0x16, False), "t": (0x17, False), "u": (0x18, False),
    "v": (0x19, False), "w": (0x1A, False), "x": (0x1B, False),
    "y": (0x1C, False), "z": (0x1D, False),
    "A": (0x04, True), "B": (0x05, True), "C": (0x06, True),
    "D": (0x07, True), "E": (0x08, True), "F": (0x09, True),
    "G": (0x0A, True), "H": (0x0B, True), "I": (0x0C, True),
    "J": (0x0D, True), "K": (0x0E, True), "L": (0x0F, True),
    "M": (0x10, True), "N": (0x11, True), "O": (0x12, True),
    "P": (0x13, True), "Q": (0x14, True), "R": (0x15, True),
    "S": (0x16, True), "T": (0x17, True), "U": (0x18, True),
    "V": (0x19, True), "W": (0x1A, True), "X": (0x1B, True),
    "Y": (0x1C, True), "Z": (0x1D, True),
    "1": (0x1E, False), "2": (0x1F, False), "3": (0x20, False),
    "4": (0x21, False), "5": (0x22, False), "6": (0x23, False),
    "7": (0x24, False), "8": (0x25, False), "9": (0x26, False),
    "0": (0x27, False),
    "\n": (0x28, False), "\t": (0x2B, False), " ": (0x2C, False),
    "-": (0x2D, False), "=": (0x2E, False), "[": (0x2F, False),
    "]": (0x30, False), "\\": (0x31, False), ";": (0x33, False),
    "'": (0x34, False), "`": (0x35, False), ",": (0x36, False),
    ".": (0x37, False), "/": (0x38, False),
    # Shifted symbols
    "!": (0x1E, True), "@": (0x1F, True), "#": (0x20, True),
    "$": (0x21, True), "%": (0x22, True), "^": (0x23, True),
    "&": (0x24, True), "*": (0x25, True), "(": (0x26, True),
    ")": (0x27, True), "_": (0x2D, True), "+": (0x2E, True),
    "{": (0x2F, True), "}": (0x30, True), "|": (0x31, True),
    ":": (0x33, True), '"': (0x34, True), "~": (0x35, True),
    "<": (0x36, True), ">": (0x37, True), "?": (0x38, True),
}


def keyname_to_code(name):
    """Resolve a key name to (modifier_bits, keycode) or None."""
    lower = name.lower()
    if lower in MODIFIER_KEYS:
        return (MODIFIER_KEYS[lower], 0x00)
    if lower in KEYCODES:
        return (0x00, KEYCODES[lower])
    return None


def char_to_report(ch):
    """Return (modifier_bits, keycode) for a typeable character, or None."""
    entry = CHAR_MAP.get(ch)
    if entry is None:
        return None
    keycode, shift = entry
    mod = MOD_LEFT_SHIFT if shift else MOD_NONE
    return (mod, keycode)
