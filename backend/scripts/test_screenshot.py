import sys
import os
import json
import asyncio
import base64
import subprocess
import httpx
import websockets

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
CDP_PORT = 9222
USER_DATA_DIR = r"C:\Users\marke\.gemini\antigravity-ide\brain\285e3580-0983-4642-8c62-ad74e048a2fc\scratch\chrome_test_profile"

async def main():
    subprocess.run("taskkill /F /IM chrome.exe /T", shell=True, capture_output=True)
    await asyncio.sleep(1)
    
    proc = subprocess.Popen([
        CHROME_PATH,
        f"--remote-debugging-port={CDP_PORT}",
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        f"--user-data-dir={USER_DATA_DIR}",
        "--window-size=1440,900"
    ])
    await asyncio.sleep(2)
    
    try:
        r = httpx.get(f"http://127.0.0.1:{CDP_PORT}/json/list")
        ws_url = r.json()[0]["webSocketDebuggerUrl"]
        print("Connected to:", ws_url, flush=True)
        
        async with websockets.connect(ws_url, max_size=100*1024*1024) as ws:
            pending = {}
            counter = 0
            
            async def call(method, params=None):
                nonlocal counter
                counter += 1
                mid = counter
                fut = asyncio.get_running_loop().create_future()
                pending[mid] = fut
                await ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
                return await fut
                
            async def listener():
                async for raw in ws:
                    msg = json.loads(raw)
                    mid = msg.get("id")
                    if mid and mid in pending:
                        pending.pop(mid).set_result(msg)
            
            t = asyncio.create_task(listener())
            
            await call("Page.enable")
            await call("Runtime.enable")
            await call("Page.navigate", {"url": "http://localhost:3000/login"})
            await asyncio.sleep(2)
            
            print("Taking screenshot...", flush=True)
            res = await call("Page.captureScreenshot", {"format": "png"})
            b64 = res.get("result", {}).get("data", "")
            print("Screenshot data length:", len(b64), flush=True)
            
            t.cancel()
    finally:
        subprocess.run(f"taskkill /F /PID {proc.pid} /T", shell=True, capture_output=True)

if __name__ == "__main__":
    asyncio.run(main())
