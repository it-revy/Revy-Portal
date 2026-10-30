import asyncio
import httpx
import websockets
import json
import subprocess
import tempfile
import time

chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
user_data_dir = tempfile.mkdtemp(prefix="chrome_inspect_")

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

async def inspect():
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
            await asyncio.sleep(1)
            
            # Login
            await call("Runtime.evaluate", {"expression": "document.getElementById('username-input').focus()"})
            await call("Input.insertText", {"text": "stg4_sales_exec"})
            await call("Runtime.evaluate", {"expression": "document.getElementById('password-input').focus()"})
            await call("Input.insertText", {"text": "Pass123!"})
            await call("Runtime.evaluate", {"expression": "document.querySelector('form button[type=\"submit\"]').click()"})
            
            for _ in range(30):
                await asyncio.sleep(0.5)
                tok = await call("Runtime.evaluate", {"expression": "localStorage.getItem('token')"})
                if tok.get("result", {}).get("result", {}).get("value"):
                    break
            
            # Wait for portal to load
            for _ in range(20):
                await asyncio.sleep(0.5)
                cur_url = await call("Runtime.evaluate", {"expression": "window.location.pathname"})
                if cur_url.get("result", {}).get("result", {}).get("value") == "/portal":
                    break
            
            # Click CRM card
            await call("Runtime.evaluate", {"expression": """(() => {
                const crmCard = Array.from(document.querySelectorAll('.portal-card, .portal-service-card, h3, div')).find(el => el.innerText === 'CRM');
                if (crmCard) { crmCard.click(); return true; }
                return false;
            })()"""})
            await asyncio.sleep(2)
            
            # Click Opportunities in CrmSidebar
            await call("Runtime.evaluate", {"expression": """(() => {
                const oppLink = document.querySelector('a[href="/crm/opportunities"]') || Array.from(document.querySelectorAll('a')).find(a => a.innerText.includes('Opportunities'));
                if (oppLink) { oppLink.click(); return true; }
                return false;
            })()"""})
            await asyncio.sleep(3)
            
            url = await call("Runtime.evaluate", {"expression": "window.location.href"})
            body = await call("Runtime.evaluate", {"expression": "document.body.innerText"})
            print("URL:", url["result"]["result"].get("value"), flush=True)
            print("Body snippet:\n", body["result"]["result"].get("value")[:600], flush=True)
            t.cancel()
    finally:
        subprocess.run(f"taskkill /F /PID {proc.pid} /T", shell=True, capture_output=True)

if __name__ == "__main__":
    asyncio.run(inspect())
