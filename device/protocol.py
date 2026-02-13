# Command parser for USB HID text protocol
# All commands are newline-terminated ASCII.

from keycodes import keyname_to_code, char_to_report, MODIFIER_KEYS


class Command:
    """Parsed command with type and parameters."""
    __slots__ = ("kind", "params")

    def __init__(self, kind, params=None):
        self.kind = kind
        self.params = params or {}


def parse(line):
    """Parse a command line into a Command object.

    Returns a Command on success, or a string error message on failure.
    """
    line = line.strip()
    if not line:
        return "empty command"

    parts = line.split(None, 1)
    verb = parts[0].lower()
    rest = parts[1] if len(parts) > 1 else ""

    # --- System commands ---
    if verb == "ping":
        return Command("ping")

    if verb == "reset":
        return Command("reset")

    if verb == "releaseall":
        return Command("releaseall")

    if verb == "bootloader":
        return Command("bootloader")

    # --- Keyboard: key <name> ---
    if verb == "key":
        if not rest:
            return "key: missing key name"
        resolved = keyname_to_code(rest.strip())
        if resolved is None:
            return "key: unknown key '{}'".format(rest.strip())
        mod, code = resolved
        return Command("key", {"mod": mod, "code": code})

    # --- Keyboard: keydown <name> ---
    if verb == "keydown":
        if not rest:
            return "keydown: missing key name"
        resolved = keyname_to_code(rest.strip())
        if resolved is None:
            return "keydown: unknown key '{}'".format(rest.strip())
        mod, code = resolved
        return Command("keydown", {"mod": mod, "code": code})

    # --- Keyboard: keyup <name> ---
    if verb == "keyup":
        if not rest:
            return "keyup: missing key name"
        resolved = keyname_to_code(rest.strip())
        if resolved is None:
            return "keyup: unknown key '{}'".format(rest.strip())
        mod, code = resolved
        return Command("keyup", {"mod": mod, "code": code})

    # --- Keyboard: mod <mods> <key> ---
    if verb == "mod":
        if not rest:
            return "mod: missing modifiers and key"
        mod_parts = rest.split()
        if len(mod_parts) < 2:
            return "mod: need <mods> <key>"
        mod_str = mod_parts[0]
        key_name = mod_parts[1]
        # Parse modifier combo like "ctrl+shift"
        mod_bits = 0
        for m in mod_str.lower().split("+"):
            m = m.strip()
            if m not in MODIFIER_KEYS:
                return "mod: unknown modifier '{}'".format(m)
            mod_bits |= MODIFIER_KEYS[m]
        resolved = keyname_to_code(key_name)
        if resolved is None:
            return "mod: unknown key '{}'".format(key_name)
        _, code = resolved
        return Command("mod", {"mod": mod_bits, "code": code})

    # --- Keyboard: type <text> ---
    if verb == "type":
        if not rest:
            return "type: missing text"
        # Validate all characters are typeable
        chars = []
        for ch in rest:
            result = char_to_report(ch)
            if result is None:
                return "type: unsupported character '{}'".format(ch)
            chars.append(result)
        return Command("type", {"chars": chars})

    # --- Mouse commands ---
    if verb == "mouse":
        if not rest:
            return "mouse: missing subcommand"
        sub_parts = rest.split(None, 1)
        sub = sub_parts[0].lower()
        sub_rest = sub_parts[1] if len(sub_parts) > 1 else ""

        if sub == "abs":
            args = sub_rest.split()
            if len(args) < 2:
                return "mouse abs: need <x> <y>"
            try:
                x = int(args[0])
                y = int(args[1])
            except ValueError:
                return "mouse abs: x/y must be integers"
            return Command("mouse_abs", {"x": x, "y": y})

        if sub == "move":
            args = sub_rest.split()
            if len(args) < 2:
                return "mouse move: need <dx> <dy>"
            try:
                dx = int(args[0])
                dy = int(args[1])
            except ValueError:
                return "mouse move: dx/dy must be integers"
            return Command("mouse_move", {"dx": dx, "dy": dy})

        if sub == "click":
            btn = sub_rest.strip().lower()
            if not btn:
                return "mouse click: missing button"
            btn_bit = _parse_button(btn)
            if btn_bit is None:
                return "mouse click: unknown button '{}'".format(btn)
            return Command("mouse_click", {"button": btn_bit})

        if sub == "down":
            btn = sub_rest.strip().lower()
            if not btn:
                return "mouse down: missing button"
            btn_bit = _parse_button(btn)
            if btn_bit is None:
                return "mouse down: unknown button '{}'".format(btn)
            return Command("mouse_down", {"button": btn_bit})

        if sub == "up":
            btn = sub_rest.strip().lower()
            if not btn:
                return "mouse up: missing button"
            btn_bit = _parse_button(btn)
            if btn_bit is None:
                return "mouse up: unknown button '{}'".format(btn)
            return Command("mouse_up", {"button": btn_bit})

        if sub == "scroll":
            if not sub_rest.strip():
                return "mouse scroll: missing amount"
            try:
                amount = int(sub_rest.strip())
            except ValueError:
                return "mouse scroll: amount must be integer"
            return Command("mouse_scroll", {"amount": amount})

        return "mouse: unknown subcommand '{}'".format(sub)

    return "unknown command '{}'".format(verb)


# Mouse button name -> bit mask
_BUTTONS = {
    "left": 0x01,
    "right": 0x02,
    "middle": 0x04,
}


def _parse_button(name):
    return _BUTTONS.get(name)
