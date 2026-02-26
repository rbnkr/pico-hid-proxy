# WiFi connection management for Pico 2 W

import network
import time

_wlan = None


def connect(ssid, password, timeout_ms=15000):
    """Attempt WiFi connection. Returns (success, status_message)."""
    global _wlan
    _wlan = network.WLAN(network.STA_IF)
    _wlan.active(True)

    if _wlan.isconnected():
        _wlan.disconnect()

    _wlan.connect(ssid, password)

    start = time.ticks_ms()
    while not _wlan.isconnected():
        if time.ticks_diff(time.ticks_ms(), start) > timeout_ms:
            return False, "timeout connecting to '{}'".format(ssid)
        time.sleep_ms(100)

    ip = _wlan.ifconfig()[0]
    return True, "connected to '{}' ip={}".format(ssid, ip)


def disconnect():
    if _wlan is not None and _wlan.isconnected():
        _wlan.disconnect()


def is_connected():
    return _wlan is not None and _wlan.isconnected()


def get_ip():
    if _wlan and _wlan.isconnected():
        return _wlan.ifconfig()[0]
    return None


def status_str():
    if _wlan is None:
        return "wifi not initialized"
    if not _wlan.active():
        return "wifi inactive"
    if not _wlan.isconnected():
        return "wifi disconnected"
    ifcfg = _wlan.ifconfig()
    try:
        rssi = _wlan.status("rssi")
        if rssi >= -50:
            quality = "excellent"
        elif rssi >= -60:
            quality = "strong"
        elif rssi >= -70:
            quality = "good"
        elif rssi >= -80:
            quality = "fair"
        else:
            quality = "weak"
        rssi_str = " rssi={}dBm ({})".format(rssi, quality)
    except Exception:
        rssi_str = ""
    return "connected ip={} subnet={} gw={} dns={}{}".format(*ifcfg, rssi_str)
