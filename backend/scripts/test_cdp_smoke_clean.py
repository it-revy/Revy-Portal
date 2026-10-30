import os
import sys
import json
import time
import base64
import asyncio
import tempfile
import subprocess
import httpx
import websockets

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
SCREENSHOT_DIR = r"C:\Users\marke\.gemini\antigravity-ide\brain\285e3580-0983-4642-8c62-ad74e048a2fc\screenshots"
BASE_URL = "http://localhost:3000"

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

class CDPBrowser:
    def __init__(self, port=9222):
        self.port = port
        self.proc = None
        self.user_data_dir = None
        self.ws = None
        self.pending = {}
        self.counter = 0
        self.console_logs = []
        self.failed_requests = []
        self._reader_task = None

    def start(self):
        # Clean any stale chrome instances on port
        subprocess.run("taskkill /F /IM chrome.exe", shell=True, capture_output=True)
        time.sleep(1)
        
        self.user_data_dir = tempfile.mkdtemp(prefix="chrome_cdp_")
        cmd = [
            CHROME_PATH,
            "--headless=new",
            f"--remote-debugging-port={self.port}",
            "--disable-gpu",
            "--no-sandbox",
            f"--user-data-dir={self.user_data_dir}",
            "--window-size=1440,900",
            "about:blank"
        ]
        self.proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)

    def stop(self):
        if self._reader_task:
            self._reader_task.cancel()
        if self.proc:
            try:
                subprocess.run(f"taskkill /F /PID {self.proc.pid} /T", shell=True, capture_output=True)
            except Exception:
                pass
            self.proc = None

    async def connect(self, initial_url=f"{BASE_URL}/login"):
        resp = httpx.put(f"http://127.0.0.1:{self.port}/json/new?{initial_url}", timeout=10)
        target = resp.json()
        self.ws_url = target["webSocketDebuggerUrl"]
        self.ws = await websockets.connect(self.ws_url, max_size=25 * 1024 * 1024)
        
        self._reader_task = asyncio.create_task(self._reader_loop())
        
        await self.call("Runtime.enable")
        await self.call("Page.enable")
        await self.call("Console.enable")
        await self.call("Network.enable")
        await asyncio.sleep(1)

    async def _reader_loop(self):
        try:
            async for raw in self.ws:
                msg = json.loads(raw)
                mid = msg.get("id")
                if mid in self.pending and not self.pending[mid].done():
                    self.pending[mid].set_result(msg)
                
                method = msg.get("method")
                if method == "Console.messageAdded":
                    text = msg.get("params", {}).get("message", {}).get("text", "")
                    level = msg.get("params", {}).get("message", {}).get("level", "")
                    self.console_logs.append({"level": level, "text": text})
                elif method == "Runtime.consoleAPICalled":
                    args = msg.get("params", {}).get("args", [])
                    t = msg.get("params", {}).get("type", "log")
                    val_str = " ".join([str(a.get("value", a.get("description", ""))) for a in args])
                    self.console_logs.append({"level": t, "text": val_str})
                elif method == "Network.responseReceived":
                    resp = msg.get("params", {}).get("response", {})
                    status = resp.get("status", 200)
                    url = resp.get("url", "")
                    if status >= 400 and not url.endswith((".ico", ".map", ".woff", ".woff2")):
                        self.failed_requests.append({"url": url, "status": status, "statusText": resp.get("statusText", "")})
        except asyncio.CancelledError:
            pass
        except Exception:
            pass

    async def call(self, method, params=None):
        self.counter += 1
        mid = self.counter
        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        self.pending[mid] = fut
        
        payload = {"id": mid, "method": method, "params": params or {}}
        await self.ws.send(json.dumps(payload))
        res = await asyncio.wait_for(fut, timeout=25)
        return res

    async def navigate(self, url, wait_sec=2):
        await self.call("Page.navigate", {"url": url})
        await asyncio.sleep(wait_sec)

    async def evaluate(self, expr):
        res = await self.call("Runtime.evaluate", {
            "expression": expr,
            "returnByValue": True,
            "awaitPromise": True
        })
        val = res.get("result", {}).get("result", {})
        if "value" in val:
            return val["value"]
        return val

    async def screenshot(self, name):
        res = await self.call("Page.captureScreenshot", {"format": "png"})
        b64 = res.get("result", {}).get("data", "")
        if b64:
            path = os.path.join(SCREENSHOT_DIR, name)
            with open(path, "wb") as f:
                f.write(base64.b64decode(b64))
            print(f"[SCREENSHOT] Saved: {name}", flush=True)
            return path
        return None

    async def login_user(self, username, password):
        # Helper to set input using React prototype value setter
        js_login = f"""(() => {{
            const setVal = (el, val) => {{
                if (!el) return;
                const proto = el instanceof HTMLTextAreaElement ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
                Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, val);
                el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                el.dispatchEvent(new Event('change', {{ bubbles: true }}));
            }};
            const u = document.getElementById('username-input');
            const p = document.getElementById('password-input');
            setVal(u, '{username}');
            setVal(p, '{password}');
            const btn = document.querySelector('form button[type="submit"]');
            if (btn) btn.click();
        }})()"""
        
        await self.evaluate(js_login)
        
        # Wait up to 15s for token in localStorage
        token_found = False
        for _ in range(30):
            await asyncio.sleep(0.5)
            tok = await self.evaluate("localStorage.getItem('token')")
            if tok:
                token_found = True
                break
        
        await asyncio.sleep(1.5)
        return token_found

    async def logout_user(self):
        await self.evaluate("localStorage.clear(); sessionStorage.clear();")
        await self.navigate(f"{BASE_URL}/login", wait_sec=1.5)


async def main():
    browser = CDPBrowser()
    browser.start()
    try:
        print("[INIT] Connecting to Chrome CDP...", flush=True)
        await browser.connect(f"{BASE_URL}/login")
        await asyncio.sleep(2)
        
        # Test 1: Sales Exec Login
        print("[TEST] Testing login for stg4_sales_exec...", flush=True)
        success = await browser.login_user("stg4_sales_exec", "Pass123!")
        curr_url = await browser.evaluate("window.location.href")
        print(f"[TEST] Login success: {success}, Current URL: {curr_url}", flush=True)
        await browser.screenshot("01_after_sales_exec_login.png")
        
        # Test 2: Navigate to Opportunities Kanban
        print("[TEST] Navigating to /crm/opportunities...", flush=True)
        await browser.navigate(f"{BASE_URL}/crm/opportunities", wait_sec=3)
        await browser.screenshot("02_crm_opportunities.png")
        
        stages = await browser.evaluate("""(() => {
            const expected = ['Enquiry', 'Qualify', 'Develop', 'Propose/Offer', 'Negotiate', 'Close'];
            const text = document.body.innerText;
            return expected.filter(s => text.includes(s));
        })()""")
        print(f"[TEST] Stages detected: {stages}", flush=True)
        
    finally:
        browser.stop()

if __name__ == "__main__":
    asyncio.run(main())
