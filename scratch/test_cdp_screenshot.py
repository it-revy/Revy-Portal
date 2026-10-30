import asyncio
import subprocess
import httpx
import websockets
import json
import os
import sys

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
USER_DATA = r"C:\Users\marke\.gemini\antigravity-ide\brain\285e3580-0983-4642-8c62-ad74e048a2fc\scratch\chrome_test_profile_diag"
os.makedirs(USER_DATA, exist_ok=True)

subprocess.run("taskkill /F /IM chrome.exe /T", shell=True, capture_output=True)
p = subprocess.Popen([
    CHROME,
    "--remote-debugging-port=9222",
    "--headless=new",
    "--disable-gpu",
    "--no-sandbox",
    f"--user-data-dir={USER_DATA}",
    "--window-size=1440,900"
], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

async def main():
    try:
        await asyncio.sleep(2)
        async with httpx.AsyncClient() as client:
            r = await client.get("http://127.0.0.1:9222/json/list", timeout=5)
            tabs = r.json()
            print("Tabs:", len(tabs))
            ws_url = tabs[0]["webSocketDebuggerUrl"]
        
        async with websockets.connect(ws_url, max_size=100*1024*1024) as ws:
            await ws.send(json.dumps({"id": 1, "method": "Page.enable"}))
            print("Page.enable response:", await ws.recv())
            
            await ws.send(json.dumps({"id": 2, "method": "Page.navigate", "params": {"url": "http://localhost:3000/login"}}))
            print("Page.navigate response:", await ws.recv())
            await asyncio.sleep(2)
            
            await ws.send(json.dumps({"id": 3, "method": "Page.captureScreenshot", "params": {"format": "png"}}))
            raw = await asyncio.wait_for(ws.recv(), timeout=10)
            print("captureScreenshot response len:", len(raw))
    finally:
        subprocess.run(f"taskkill /F /PID {p.pid} /T", shell=True, capture_output=True)

asyncio.run(main())
