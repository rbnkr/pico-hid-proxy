# main.py — Async command loop for USB HID keyboard+mouse + WiFi web control
# Reads newline-terminated ASCII commands from CDC serial and/or HTTP API,
# dispatches to keyboard/mouse HID devices.

import sys
import time
import select
import machine
import micropython
import uasyncio as asyncio

from boot import keyboard, mouse, abs_mouse
from protocol import parse, Command
import config
import wifi


def _respond(msg):
    """Write a response line to serial output."""
    sys.stdout.write(msg + "\n")


_web_server_started = False


def _dispatch(cmd, from_web=False):
    """Execute a parsed command. Returns response string."""
    k = cmd.kind
    p = cmd.params

    # System
    if k == "ping":
        return "PONG"
    if k == "reset":
        keyboard.release_all()
        mouse.release_all()
        return "OK"
    if k == "releaseall":
        keyboard.release_all()
        return "OK"
    if k == "bootloader":
        _respond("OK")
        time.sleep(0.1)
        machine.bootloader()
        return None

    # WiFi / Web
    if k == "wifi_set":
        config.set_wifi(p["ssid"], p["password"])
        return "OK credentials saved for '{}'".format(p["ssid"])
    if k == "wifi_get":
        ssid, password = config.get_wifi()
        if not ssid:
            return "no saved wifi credentials"
        if from_web:
            password = "****"
        return "ssid={} password={}".format(ssid, password)
    if k == "wifi_connect":
        ssid = p.get("ssid")
        password = p.get("password")
        if ssid and password:
            config.set_wifi(ssid, password)
        else:
            ssid, password = config.get_wifi()
            if not ssid or not password:
                return "ERR no saved wifi credentials (use wifi set <ssid> <password>)"
        ok, msg = wifi.connect(ssid, password)
        if ok:
            _try_start_web()
        return ("OK " + msg) if ok else ("ERR " + msg)
    if k == "wifi_disconnect":
        wifi.disconnect()
        return "OK disconnected"
    if k == "wifi_status":
        return wifi.status_str()
    if k == "wifi_clear":
        wifi.disconnect()
        config.clear_wifi()
        return "OK wifi credentials cleared"
    if k == "api_token":
        config.set_web_password(p["token"])
        if _web_server_started:
            import web
            web.set_password(p["token"])
        return "OK api token set"
    if k == "api_enable":
        if not config.get_web_password():
            return "ERR no api token set (use api token <value> first)"
        config.set_api_enabled(True)
        if _web_server_started:
            import web
            web.set_api_enabled(True)
        _try_start_web()
        return "OK api enabled"
    if k == "api_disable":
        config.set_api_enabled(False)
        config.set_webui_enabled(False)
        if _web_server_started:
            import web
            web.set_api_enabled(False)
            web.set_webui_enabled(False)
        return "OK api disabled (webui also disabled)"
    if k == "api_status":
        enabled = config.get_api_enabled()
        running = _web_server_started and enabled
        state = "enabled" if enabled else "disabled"
        return "api {} ({})".format(state, "running" if running else "stopped")
    if k == "webui_enable":
        if not config.get_web_password():
            return "ERR no api token set (use api token <value> first)"
        config.set_webui_enabled(True)
        config.set_api_enabled(True)
        if _web_server_started:
            import web
            web.set_webui_enabled(True)
            web.set_api_enabled(True)
        _try_start_web()
        return "OK webui enabled (api also enabled)"
    if k == "webui_disable":
        config.set_webui_enabled(False)
        if _web_server_started:
            import web
            web.set_webui_enabled(False)
        return "OK webui disabled"
    if k == "webui_status":
        enabled = config.get_webui_enabled()
        running = _web_server_started and enabled
        state = "enabled" if enabled else "disabled"
        return "webui {} ({})".format(state, "running" if running else "stopped")
    if k == "status":
        lines = []
        ssid, _ = config.get_wifi()
        lines.append("wifi credentials: {}".format("set" if ssid else "not set"))
        lines.append("wifi: {}".format(wifi.status_str()))
        api_on = config.get_api_enabled()
        api_running = _web_server_started and api_on
        lines.append("api: {} ({})".format(
            "enabled" if api_on else "disabled",
            "running" if api_running else "stopped"))
        webui_on = config.get_webui_enabled()
        webui_running = _web_server_started and webui_on
        lines.append("webui: {} ({})".format(
            "enabled" if webui_on else "disabled",
            "running" if webui_running else "stopped"))
        return "\n".join(lines)

    # Keyboard
    if k == "key":
        keyboard.press_key(p["mod"], p["code"])
        return "OK"
    if k == "keydown":
        keyboard.key_down(p["mod"], p["code"])
        return "OK"
    if k == "keyup":
        keyboard.key_up(p["mod"], p["code"])
        return "OK"
    if k == "mod":
        keyboard.mod_key(p["mod"], p["code"])
        return "OK"
    if k == "type":
        keyboard.type_chars(p["chars"])
        return "OK"

    # Mouse
    if k == "mouse_abs":
        abs_mouse.move_abs(p["x"], p["y"])
        return "OK"
    if k == "mouse_move":
        mouse.move(p["dx"], p["dy"])
        return "OK"
    if k == "mouse_click":
        mouse.click(p["button"])
        return "OK"
    if k == "mouse_down":
        mouse.button_down(p["button"])
        return "OK"
    if k == "mouse_up":
        mouse.button_up(p["button"])
        return "OK"
    if k == "mouse_scroll":
        mouse.scroll(p["amount"])
        return "OK"

    return "ERR unknown command kind"


def _dispatch_from_web(cmd_str):
    """Entry point for web server — parse and execute a command string."""
    result = parse(cmd_str)
    if isinstance(result, str):
        return "ERR " + result
    try:
        resp = _dispatch(result, from_web=True)
        return resp if resp else "OK"
    except Exception as e:
        return "ERR " + str(e)


def _try_start_web():
    """Start web server if WiFi is connected, a token is set, and api/webui is enabled."""
    global _web_server_started
    if _web_server_started:
        return
    api_on = config.get_api_enabled()
    webui_on = config.get_webui_enabled()
    if not api_on and not webui_on:
        _respond("WEB skipped (api and webui disabled)")
        return
    web_pass = config.get_web_password()
    if not web_pass:
        _respond("WEB skipped (no webpass set)")
        return
    if not wifi.is_connected():
        return
    import web

    web.start(web_pass, _dispatch_from_web, api_on, webui_on)
    asyncio.create_task(web.run_server())
    _web_server_started = True
    ip = wifi.get_ip()
    _respond("WEB http://{}".format(ip))


async def _serial_task():
    """Async task: read and process serial commands."""
    poller = select.poll()
    poller.register(sys.stdin.buffer, select.POLLIN)
    buf = bytearray()

    while True:
        events = poller.poll(0)
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
                        await asyncio.sleep_ms(0)
                        continue
                    buf = bytearray()

                    if not line.strip():
                        await asyncio.sleep_ms(0)
                        continue

                    result = parse(line)
                    if isinstance(result, str):
                        _respond("ERR " + result)
                    else:
                        try:
                            resp = _dispatch(result)
                            if resp is not None:
                                _respond(resp)
                        except Exception as e:
                            _respond("ERR " + str(e))
                elif b == 0x0D:  # ignore CR
                    pass
                else:
                    buf.append(b)
        else:
            await asyncio.sleep_ms(1)


async def _main_async():
    """Connect WiFi if configured, start web server, run serial loop."""
    ssid, password = config.get_wifi()
    if ssid and password:
        try:
            ok, msg = wifi.connect(ssid, password)
            if ok:
                _respond("WIFI " + msg)
                _try_start_web()
            else:
                _respond("WIFI " + msg)
        except Exception:
            pass

    await _serial_task()


def main():
    time.sleep(2)
    micropython.kbd_intr(-1)

    try:
        asyncio.run(_main_async())
    except KeyboardInterrupt:
        pass


main()
