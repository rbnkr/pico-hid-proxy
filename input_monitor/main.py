"""
Input Monitor - Detects real vs emulated keyboard and mouse input.

Uses Windows low-level hooks (WH_KEYBOARD_LL / WH_MOUSE_LL) to inspect
the INJECTED flag that the OS sets on synthetic input events.

Run from a Windows Python interpreter (not WSL) with:
    python main.py

Press Ctrl+C in the console to quit.
"""

import ctypes
import ctypes.wintypes as wt
import sys
import time
from collections import namedtuple
from ctypes import CFUNCTYPE, POINTER, Structure, c_int, windll, wintypes

# ── Win32 constants ──────────────────────────────────────────────────────────

WH_KEYBOARD_LL = 13
WH_MOUSE_LL = 14

# Keyboard messages
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105

# Mouse messages
WM_MOUSEMOVE = 0x0200
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP = 0x0205
WM_MBUTTONDOWN = 0x0207
WM_MBUTTONUP = 0x0208
WM_MOUSEWHEEL = 0x020A
WM_MOUSEHWHEEL = 0x020E
WM_XBUTTONDOWN = 0x020B
WM_XBUTTONUP = 0x020C

# Low-level hook injected flags
LLKHF_INJECTED = 0x00000010
LLMHF_INJECTED = 0x00000001

HC_ACTION = 0

# ── Structures ───────────────────────────────────────────────────────────────

class KBDLLHOOKSTRUCT(Structure):
    _fields_ = [
        ("vkCode", wt.DWORD),
        ("scanCode", wt.DWORD),
        ("flags", wt.DWORD),
        ("time", wt.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class MSLLHOOKSTRUCT(Structure):
    _fields_ = [
        ("pt", wt.POINT),
        ("mouseData", wt.DWORD),
        ("flags", wt.DWORD),
        ("time", wt.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class POINT(Structure):
    _fields_ = [("x", wt.LONG), ("y", wt.LONG)]


# ── Hook callback type ───────────────────────────────────────────────────────

HOOKPROC = CFUNCTYPE(ctypes.c_long, c_int, wt.WPARAM, wt.LPARAM)

# ── Win32 API bindings ───────────────────────────────────────────────────────

user32 = windll.user32
kernel32 = windll.kernel32

SetWindowsHookExW = user32.SetWindowsHookExW
SetWindowsHookExW.restype = wt.HHOOK
SetWindowsHookExW.argtypes = [c_int, HOOKPROC, wt.HINSTANCE, wt.DWORD]

CallNextHookEx = user32.CallNextHookEx
CallNextHookEx.restype = ctypes.c_long
CallNextHookEx.argtypes = [wt.HHOOK, c_int, wt.WPARAM, wt.LPARAM]

UnhookWindowsHookEx = user32.UnhookWindowsHookEx
UnhookWindowsHookEx.restype = wt.BOOL
UnhookWindowsHookEx.argtypes = [wt.HHOOK]

GetMessageW = user32.GetMessageW
GetMessageW.argtypes = [ctypes.POINTER(wt.MSG), wt.HWND, wt.UINT, wt.UINT]

PeekMessageW = user32.PeekMessageW
PeekMessageW.restype = wt.BOOL
PeekMessageW.argtypes = [ctypes.POINTER(wt.MSG), wt.HWND, wt.UINT, wt.UINT, wt.UINT]

TranslateMessage = user32.TranslateMessage
TranslateMessage.argtypes = [ctypes.POINTER(wt.MSG)]

DispatchMessageW = user32.DispatchMessageW
DispatchMessageW.argtypes = [ctypes.POINTER(wt.MSG)]

PM_REMOVE = 0x0001
WM_QUIT = 0x0012

GetModuleHandleW = kernel32.GetModuleHandleW
GetModuleHandleW.restype = wt.HMODULE
GetModuleHandleW.argtypes = [wt.LPCWSTR]

GetKeyNameTextW = user32.GetKeyNameTextW
GetKeyNameTextW.restype = c_int
GetKeyNameTextW.argtypes = [wt.LONG, wt.LPWSTR, c_int]

MapVirtualKeyW = user32.MapVirtualKeyW
MapVirtualKeyW.restype = wt.UINT
MapVirtualKeyW.argtypes = [wt.UINT, wt.UINT]

# ── Friendly name maps ───────────────────────────────────────────────────────

KB_MSG_NAMES = {
    WM_KEYDOWN: "KEY_DOWN",
    WM_KEYUP: "KEY_UP",
    WM_SYSKEYDOWN: "SYSKEY_DOWN",
    WM_SYSKEYUP: "SYSKEY_UP",
}

MOUSE_MSG_NAMES = {
    WM_MOUSEMOVE: "MOVE",
    WM_LBUTTONDOWN: "L_DOWN",
    WM_LBUTTONUP: "L_UP",
    WM_RBUTTONDOWN: "R_DOWN",
    WM_RBUTTONUP: "R_UP",
    WM_MBUTTONDOWN: "M_DOWN",
    WM_MBUTTONUP: "M_UP",
    WM_MOUSEWHEEL: "WHEEL",
    WM_MOUSEHWHEEL: "HWHEEL",
    WM_XBUTTONDOWN: "X_DOWN",
    WM_XBUTTONUP: "X_UP",
}

# ── Colours (ANSI) ───────────────────────────────────────────────────────────

GREEN = "\033[92m"
RED = "\033[91m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"


# ── Helpers ──────────────────────────────────────────────────────────────────

def get_key_name(vk_code: int, scan_code: int) -> str:
    """Return a human-readable key name for the given virtual-key code."""
    buf = ctypes.create_unicode_buffer(64)
    # Build the lParam expected by GetKeyNameText (scan code in bits 16-23)
    if scan_code == 0:
        scan_code = MapVirtualKeyW(vk_code, 0)
    lparam = scan_code << 16
    length = GetKeyNameTextW(lparam, buf, 64)
    if length:
        return buf.value
    return f"VK_0x{vk_code:02X}"


def origin_label(is_injected: bool) -> str:
    if is_injected:
        return f"{RED}{BOLD}EMULATED{RESET}"
    return f"{GREEN}{BOLD}HARDWARE{RESET}"


# ── Callback implementations ────────────────────────────────────────────────

def _keyboard_hook_proc(nCode, wParam, lParam):
    if nCode == HC_ACTION:
        kb = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
        injected = bool(kb.flags & LLKHF_INJECTED)
        action = KB_MSG_NAMES.get(wParam, f"0x{wParam:04X}")
        key_name = get_key_name(kb.vkCode, kb.scanCode)

        print(
            f"  {CYAN}[KB]{RESET}  "
            f"{action:<12} "
            f"key={YELLOW}{key_name:<20}{RESET} "
            f"vk=0x{kb.vkCode:02X}  scan=0x{kb.scanCode:02X}  "
            f"flags=0x{kb.flags:08X}  "
            f"{origin_label(injected)}"
        )

    return CallNextHookEx(None, nCode, wParam, lParam)


def _mouse_hook_proc(nCode, wParam, lParam):
    if nCode == HC_ACTION:
        ms = ctypes.cast(lParam, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
        injected = bool(ms.flags & LLMHF_INJECTED)
        action = MOUSE_MSG_NAMES.get(wParam, f"0x{wParam:04X}")

        # Skip noisy MOVE events unless they're emulated
        if wParam == WM_MOUSEMOVE and not injected:
            return CallNextHookEx(None, nCode, wParam, lParam)

        extra = ""
        if wParam in (WM_MOUSEWHEEL, WM_MOUSEHWHEEL):
            delta = ctypes.c_short(ms.mouseData >> 16).value
            extra = f"delta={delta}  "

        print(
            f"  {YELLOW}[MS]{RESET}  "
            f"{action:<12} "
            f"pos=({ms.pt.x:5}, {ms.pt.y:5})  "
            f"{extra}"
            f"flags=0x{ms.flags:08X}  "
            f"{origin_label(injected)}"
        )

    return CallNextHookEx(None, nCode, wParam, lParam)


# Prevent garbage collection of the callback pointers
_kb_hook_proc = HOOKPROC(_keyboard_hook_proc)
_ms_hook_proc = HOOKPROC(_mouse_hook_proc)


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    print(f"\n{BOLD}=== Input Monitor ==={RESET}")
    print(f"Listening for keyboard and mouse events.")
    print(f"Real hardware input  -> {GREEN}{BOLD}HARDWARE{RESET}")
    print(f"Injected / emulated  -> {RED}{BOLD}EMULATED{RESET}")
    print(f"{DIM}(Real mouse MOVE events are hidden to reduce noise){RESET}")
    print(f"Press Ctrl+C to quit.\n")

    h_mod = GetModuleHandleW(None)

    kb_hook = SetWindowsHookExW(WH_KEYBOARD_LL, _kb_hook_proc, h_mod, 0)
    if not kb_hook:
        print("Failed to install keyboard hook.", file=sys.stderr)
        sys.exit(1)

    ms_hook = SetWindowsHookExW(WH_MOUSE_LL, _ms_hook_proc, h_mod, 0)
    if not ms_hook:
        print("Failed to install mouse hook.", file=sys.stderr)
        UnhookWindowsHookEx(kb_hook)
        sys.exit(1)

    print(f"{DIM}Hooks installed. Waiting for input...{RESET}\n")

    msg = wt.MSG()
    try:
        while True:
            # Use PeekMessage instead of GetMessage so we yield back to
            # Python between iterations, allowing Ctrl+C to be processed.
            if PeekMessageW(ctypes.byref(msg), None, 0, 0, PM_REMOVE):
                if msg.message == WM_QUIT:
                    break
                TranslateMessage(ctypes.byref(msg))
                DispatchMessageW(ctypes.byref(msg))
            else:
                time.sleep(0.01)
    except KeyboardInterrupt:
        pass
    finally:
        UnhookWindowsHookEx(kb_hook)
        UnhookWindowsHookEx(ms_hook)
        print(f"\n{BOLD}Hooks removed. Goodbye.{RESET}")


if __name__ == "__main__":
    main()
