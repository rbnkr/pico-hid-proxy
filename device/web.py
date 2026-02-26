# Minimal async HTTP server for Pico HID web control
# Serves a public HTML page and a token-authenticated JSON API endpoint.

import json
import uasyncio as asyncio

_dispatch_fn = None
_web_password = None
_api_enabled = False
_webui_enabled = False

_HTML = """\
<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pico HID Proxy</title>
<style>
*{box-sizing:border-box}
body{font-family:system-ui,sans-serif;max-width:520px;margin:20px auto;padding:0 12px;background:#1a1a2e;color:#e0e0e0}
h2{color:#0ff;margin-bottom:4px}
label{display:block;margin-top:10px;font-size:14px;color:#aaa}
input,button{font-size:15px;padding:8px;width:100%;border:1px solid #333;border-radius:4px;background:#16213e;color:#e0e0e0}
input:focus{outline:none;border-color:#0ff}
button{margin-top:14px;background:#0ff;color:#1a1a2e;font-weight:bold;border:none;cursor:pointer}
button:active{background:#0aa}
#res{margin-top:12px;padding:8px;background:#0d1117;border-radius:4px;min-height:24px;font-family:monospace;white-space:pre-wrap;font-size:14px}
details{margin-top:18px;font-size:13px;color:#888}
summary{cursor:pointer;color:#0ff;font-size:14px}
table{width:100%;border-collapse:collapse;margin-top:6px}
td{padding:3px 6px;border-bottom:1px solid #222;font-family:monospace;font-size:12px}
td:first-child{color:#7ec8e3;white-space:nowrap}
</style></head><body>
<h2>Pico HID Proxy</h2>
<label>Command</label>
<input id="cmd" placeholder="e.g. key tap a, key type Hello, mouse move 10 20" autofocus>
<label>Delay (ms)</label>
<input id="delay" type="number" value="0" min="0" step="500">
<label>Token</label>
<input id="token" type="password" placeholder="Set via: api token <value>">
<button onclick="send()">Execute</button>
<div id="res"></div>
<details><summary>Command Reference</summary><table>
<tr><td colspan="2" style="color:#0ff;font-weight:bold;border:none;padding-top:8px">Keyboard</td></tr>
<tr><td>key tap &lt;name&gt;</td><td>Press &amp; release key</td></tr>
<tr><td>key down &lt;name&gt;</td><td>Hold key down</td></tr>
<tr><td>key up &lt;name&gt;</td><td>Release key</td></tr>
<tr><td>key mod &lt;mods&gt; &lt;key&gt;</td><td>Modifier combo (e.g. key mod ctrl+shift esc)</td></tr>
<tr><td>key type &lt;text&gt;</td><td>Type a string</td></tr>
<tr><td>key release</td><td>Release all held keys</td></tr>
<tr><td colspan="2" style="color:#0ff;font-weight:bold;border:none;padding-top:8px">Mouse</td></tr>
<tr><td>mouse move &lt;dx&gt; &lt;dy&gt;</td><td>Relative mouse move</td></tr>
<tr><td>mouse abs &lt;x&gt; &lt;y&gt;</td><td>Absolute position (0-32767)</td></tr>
<tr><td>mouse click &lt;btn&gt;</td><td>Click left/right/middle</td></tr>
<tr><td>mouse down &lt;btn&gt;</td><td>Hold mouse button</td></tr>
<tr><td>mouse up &lt;btn&gt;</td><td>Release mouse button</td></tr>
<tr><td>mouse scroll &lt;n&gt;</td><td>Scroll wheel (+ up, - down)</td></tr>
<tr><td>mouse release</td><td>Release all held buttons</td></tr>
<tr><td colspan="2" style="color:#0ff;font-weight:bold;border:none;padding-top:8px">WiFi</td></tr>
<tr><td>wifi set &lt;ssid&gt; &lt;pass&gt;</td><td>Save WiFi credentials</td></tr>
<tr><td>wifi get</td><td>Show saved credentials</td></tr>
<tr><td>wifi connect [ssid] [pass]</td><td>Connect (use saved if no args)</td></tr>
<tr><td>wifi disconnect</td><td>Disconnect WiFi</td></tr>
<tr><td>wifi status</td><td>Show WiFi status</td></tr>
<tr><td>wifi clear</td><td>Delete saved credentials</td></tr>
<tr><td colspan="2" style="color:#0ff;font-weight:bold;border:none;padding-top:8px">API</td></tr>
<tr><td>api token &lt;value&gt;</td><td>Set API token</td></tr>
<tr><td>api enable / disable</td><td>Enable or disable API</td></tr>
<tr><td>api status</td><td>Show API enabled state</td></tr>
<tr><td colspan="2" style="color:#0ff;font-weight:bold;border:none;padding-top:8px">Web UI</td></tr>
<tr><td>webui enable / disable</td><td>Enable or disable web UI</td></tr>
<tr><td>webui status</td><td>Show web UI enabled state</td></tr>
<tr><td colspan="2" style="color:#0ff;font-weight:bold;border:none;padding-top:8px">System</td></tr>
<tr><td>ping</td><td>Connection test</td></tr>
<tr><td>status</td><td>Show overall system status</td></tr>
<tr><td>reboot</td><td>Restart the Pico</td></tr>
<tr><td>reboot bootloader</td><td>Reboot into BOOTSEL mode</td></tr>
</table></details>
<details><summary>API Usage</summary>
<p style="margin:6px 0;font-size:13px">POST to <code>/api</code> with JSON body:</p>
<pre style="background:#0d1117;padding:8px;border-radius:4px;font-size:12px;overflow-x:auto">curl -X POST http://PICO_IP/api \\
  -H "Content-Type: application/json" \\
  -d '{"cmd":"key type Hello","delay":0,"token":"YOUR_TOKEN"}'</pre>
<p style="margin:6px 0;font-size:13px">Response: <code>{"ok":true,"result":"OK"}</code></p>
</details>
<script>
const $ =id=> document.getElementById(id);
window.onload=()=>{$('token').value=localStorage.getItem('hid_token')||''};
async function send(){
 const t=$('token').value;localStorage.setItem('hid_token',t);
 const cmd=$('cmd').value;
 const isReboot=cmd.trim().toLowerCase().startsWith('reboot');
 $('res').textContent='...';
 try{
  const r=await fetch('/api',{method:'POST',headers:{'Content-Type':'application/json'},
   body:JSON.stringify({cmd:cmd,delay:parseInt($('delay').value)||0,token:t})});
  const j=await r.json();
  if(j.ok){$('res').textContent=j.result;$('cmd').value=''}
  else{$('res').textContent='ERROR: '+j.error}
 }catch(e){
  if(isReboot){$('cmd').value=''}
  else{$('res').textContent='ERROR: '+e.message}
 }
 if(isReboot)waitReboot();
}
function waitReboot(){
 const el=$('res');const t0=Date.now();
 el.textContent='Rebooting... waiting for device';
 const iv=setInterval(async()=>{
  if(Date.now()-t0>60000){clearInterval(iv);el.textContent='Reboot timed out (60s)';return}
  try{const r=await fetch('/health');if(r.ok){clearInterval(iv);location.reload()}}catch(e){}
 },2000);
}
$('cmd').onkeydown=e=>{if(e.key==='Enter')send()};
</script></body></html>"""


def start(password, dispatch_fn, api_enabled=False, webui_enabled=False):
    global _dispatch_fn, _web_password, _api_enabled, _webui_enabled
    _dispatch_fn = dispatch_fn
    _web_password = password
    _api_enabled = api_enabled
    _webui_enabled = webui_enabled


def set_password(password):
    global _web_password
    _web_password = password


def set_api_enabled(val):
    global _api_enabled
    _api_enabled = bool(val)


def set_webui_enabled(val):
    global _webui_enabled
    _webui_enabled = bool(val)


def _url_decode(s):
    result = []
    i = 0
    while i < len(s):
        if s[i] == "%" and i + 2 < len(s):
            try:
                result.append(chr(int(s[i + 1 : i + 3], 16)))
                i += 3
                continue
            except ValueError:
                pass
        result.append(s[i])
        i += 1
    return "".join(result)


def _send_response(writer, status, content_type, body):
    writer.write(
        "HTTP/1.0 {} OK\r\nContent-Type: {}\r\nContent-Length: {}\r\nConnection: close\r\n\r\n".format(
            status, content_type, len(body)
        ).encode()
    )
    writer.write(body if isinstance(body, bytes) else body.encode())


async def _handle_client(reader, writer):
    try:
        request_line = await asyncio.wait_for(reader.readline(), timeout=5)
        if not request_line:
            return
        request_line = request_line.decode().strip()
        parts = request_line.split(" ")
        if len(parts) < 2:
            return
        method = parts[0]
        path = parts[1]

        # Read headers
        content_length = 0
        while True:
            line = await asyncio.wait_for(reader.readline(), timeout=5)
            if not line or line == b"\r\n" or line == b"\n":
                break
            decoded = line.decode().strip().lower()
            if decoded.startswith("content-length:"):
                try:
                    content_length = int(decoded.split(":")[1].strip())
                except ValueError:
                    pass

        # GET /health — lightweight health check (no auth required)
        if method == "GET" and path == "/health":
            _send_response(writer, 200, "application/json", '{"ok":true}')
            await writer.drain()
            return

        # GET / — serve HTML page
        if method == "GET" and path == "/":
            if not _webui_enabled:
                _send_response(writer, 404, "text/plain", "not found")
                await writer.drain()
                return
            _send_response(writer, 200, "text/html", _HTML)
            await writer.drain()
            return

        # POST /api — execute command
        if method == "POST" and path == "/api":
            if not _api_enabled:
                _send_response(writer, 404, "text/plain", "not found")
                await writer.drain()
                return

            body = b""
            if content_length > 0:
                body = await asyncio.wait_for(
                    reader.read(min(content_length, 1024)), timeout=5
                )

            try:
                data = json.loads(body)
            except ValueError:
                _send_response(
                    writer,
                    400,
                    "application/json",
                    '{"ok":false,"error":"invalid json"}',
                )
                await writer.drain()
                return

            token = data.get("token", "")
            if token != _web_password:
                _send_response(
                    writer,
                    403,
                    "application/json",
                    '{"ok":false,"error":"unauthorized"}',
                )
                await writer.drain()
                return

            cmd_str = data.get("cmd", "").strip()
            delay_ms = 0
            try:
                delay_ms = int(data.get("delay", 0))
            except (ValueError, TypeError):
                pass

            if not cmd_str:
                _send_response(
                    writer,
                    400,
                    "application/json",
                    '{"ok":false,"error":"no command"}',
                )
                await writer.drain()
                return

            # Apply delay (milliseconds)
            if delay_ms > 0:
                await asyncio.sleep_ms(delay_ms)

            result = _dispatch_fn(cmd_str) if _dispatch_fn else "ERR no dispatcher"
            resp = json.dumps({"ok": not result.startswith("ERR"), "result": result})
            _send_response(writer, 200, "application/json", resp)
            await writer.drain()
            return

        # 404 for anything else
        _send_response(writer, 404, "text/plain", "not found")
        await writer.drain()

    except Exception:
        pass
    finally:
        writer.close()
        await writer.wait_closed()


async def run_server():
    global _server
    _server = await asyncio.start_server(_handle_client, "0.0.0.0", 80)
    # Keep this task alive so _server isn't garbage collected
    while True:
        await asyncio.sleep(60)
