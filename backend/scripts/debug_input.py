import subprocess
import tempfile
import time
import json
import asyncio
import httpx
import websockets

chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
user_data_dir = tempfile.mkdtemp(prefix="chrome_test_insert_")

proc = subprocess.Popen([
    chrome_path,
    "--headless=new",
    "--remote-debugging-port=9222",
    "--disable-gpu",
    "--no-sandbox",
    f"--user-data-dir={user_data_dir}",
    "--window-size=1440,900",
    "about:blank"
])

async def main():
    try:
        await asyncio.sleep(2)
        resp = httpx.put("http://127.0.0.1:9222/json/new?http://localhost:3000/login", timeout=5)
        ws_url = resp.json()["webSocketDebuggerUrl"]
        async with websockets.connect(ws_url) as ws:
            pending = {}
            async def reader():
                async for raw in ws:
                    msg = json.loads(raw)
                    mid = msg.get("id")
                    if mid in pending and not pending[mid].done():
                        pending[mid].set_result(msg)
            t = asyncio.create_task(reader())
            
            async def call(method, params=None):
                mid = len(pending) + 1
                fut = asyncio.get_running_loop().create_future()
                pending[mid] = fut
                await ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
                res = await fut
                return res
            
            await call("Runtime.enable")
            await call("Page.enable")
            await asyncio.sleep(2)
            
            # Focus username
            await call("Runtime.evaluate", {"expression": "document.getElementById('username-input').focus()"})
            await call("Input.insertText", {"text": "stg4_sales_exec"})
            
            # Focus password
            await call("Runtime.evaluate", {"expression": "document.getElementById('password-input').focus()"})
            await call("Input.insertText", {"text": "Pass123!"})
            
            # Click submit button
            await call("Runtime.evaluate", {"expression": "document.querySelector('form button[type=\"submit\"]').click()"})
            
            # Poll for token
            token_val = None
            for i in range(25):
                await asyncio.sleep(0.5)
                res = await call("Runtime.evaluate", {"expression": "localStorage.getItem('token')"})
                token_val = res.get("result", {}).get("result", {}).get("value")
                if token_val:
                    print(f"Token received on attempt {i}!", flush=True)
                    break
            
            loc = await call("Runtime.evaluate", {"expression": "window.location.href"})
            print("URL:", loc["result"]["result"].get("value"), flush=True)
            print("Token in localStorage:", bool(token_val), flush=True)
            t.cancel()
    finally:
        subprocess.run(f"taskkill /F /PID {proc.pid} /T", shell=True, capture_output=True)

asyncio.run(main())
