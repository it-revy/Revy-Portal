import subprocess
import tempfile
import time
import json
import asyncio
import httpx
import websockets

chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
user_data_dir = tempfile.mkdtemp(prefix="chrome_login_debug_")

proc = subprocess.Popen([
    chrome_path,
    "--headless=new",
    "--remote-debugging-port=9222",
    "--disable-gpu",
    "--no-sandbox",
    f"--user-data-dir={user_data_dir}",
    "about:blank"
])

async def main():
    try:
        await asyncio.sleep(2)
        resp = httpx.put("http://127.0.0.1:9222/json/new?http://localhost:3000/login", timeout=5)
        ws_url = resp.json()["webSocketDebuggerUrl"]
        async with websockets.connect(ws_url) as ws:
            pending = {}
            console_msgs = []
            network_errors = []
            
            async def reader():
                async for raw in ws:
                    msg = json.loads(raw)
                    mid = msg.get("id")
                    if mid in pending and not pending[mid].done():
                        pending[mid].set_result(msg)
                    method = msg.get("method")
                    if method == "Network.requestWillBeSent":
                        req = msg.get("params", {}).get("request", {})
                        print(f"[REQ] {req.get('method')} {req.get('url')}", flush=True)
                    elif method == "Network.responseReceived":
                        r = msg.get("params", {}).get("response", {})
                        print(f"[RESP] {r.get('status')} {r.get('url')}", flush=True)
                    elif method == "Runtime.consoleAPICalled":
                        args = msg.get("params", {}).get("args", [])
                        t = msg.get("params", {}).get("type", "log")
                        val_str = " ".join([str(a.get("value", a.get("description", ""))) for a in args])
                        console_msgs.append((t, val_str))
            
            async def call(method, params=None):
                mid = len(pending) + 1
                fut = asyncio.get_running_loop().create_future()
                pending[mid] = fut
                await ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
                res = await fut
                return res
            
            await call("Runtime.enable")
            await call("Page.enable")
            await call("Console.enable")
            await call("Network.enable")
            await asyncio.sleep(2)
            
            # Fill inputs using native prototype setter
            js = (
                "(() => {"
                "  function setVal(el, val) {"
                "    const proto = el instanceof HTMLTextAreaElement ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;"
                "    Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, val);"
                "    el.dispatchEvent(new Event('input', { bubbles: true }));"
                "    el.dispatchEvent(new Event('change', { bubbles: true }));"
                "  }"
                "  const u = document.getElementById('username-input');"
                "  const p = document.getElementById('password-input');"
                "  setVal(u, 'stg4_sales_exec');"
                "  setVal(p, 'Pass123!');"
                "  const btn = document.querySelector('form button[type=\"submit\"]');"
                "  btn.click();"
                "})()"
            )
            
            await call("Runtime.evaluate", {"expression": js})
            
            # Poll for token
            token_val = None
            for _ in range(30):
                await asyncio.sleep(0.5)
                res = await call("Runtime.evaluate", {"expression": "localStorage.getItem('token')"})
                token_val = res["result"]["result"].get("value")
                if token_val:
                    break
            
            loc = await call("Runtime.evaluate", {"expression": "window.location.href"})
            body = await call("Runtime.evaluate", {"expression": "document.body.innerText"})
            print("URL:", loc["result"]["result"].get("value"), flush=True)
            print("Token in localStorage:", bool(token_val), flush=True)
            print("Console msgs:", console_msgs, flush=True)
            print("Network errors:", network_errors, flush=True)
            if not token["result"]["result"].get("value"):
                print("Body snippet:", body["result"]["result"].get("value")[:400], flush=True)
            
            t.cancel()
    finally:
        proc.terminate()
        proc.wait()

asyncio.run(main())
