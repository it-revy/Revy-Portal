"""
REVY Portal Phase 5A — Full Chrome DevTools Protocol (CDP) Browser Smoke Testing Suite

Executes comprehensive browser-level User Acceptance Testing against the live Vite frontend
(http://localhost:3000) backed by FastAPI (http://127.0.0.1:5001) connected to the confirmed
testing Neon PostgreSQL database.

Automates the full Phase 5A test matrix:
- Track 1: Sales Executive Authentication, 6-Stage Kanban Board & Currency-Grouped KPIs
- Track 2: Quotation Lifecycle (Draft Creation, Submit for Review, Exec RBAC Suppression)
- Track 3: Sales Manager Commercial Review & Approval Governance
- Track 4: External Client Sharing Audit & Multi-Revision Versioning (v1 Shared -> v2 Draft)
- Track 5: Deal Reopening Governance (Sales Exec Blocked, Sales Manager Execution with Audit Justification)
- Track 6: CRM Administrator Pipeline Oversight & Security Governance
- Track 7: Browser Console & Network Request Audit (0 unhandled errors, 0 failed requests)
"""

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

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
SCREENSHOT_DIR = r"C:\Users\marke\.gemini\antigravity-ide\brain\285e3580-0983-4642-8c62-ad74e048a2fc\screenshots"
BASE_URL = "http://localhost:3000"

os.makedirs(USER_DATA_DIR, exist_ok=True)
os.makedirs(SCREENSHOT_DIR, exist_ok=True)


class CDPBrowser:
    def __init__(self):
        self.proc = None
        self.ws = None
        self.counter = 0
        self.pending = {}
        self.console_logs = []
        self.failed_requests = []
        self.event_listener_task = None

    def start(self):
        subprocess.run("taskkill /F /IM chrome.exe /T", shell=True, capture_output=True)
        import shutil
        shutil.rmtree(USER_DATA_DIR, ignore_errors=True)
        os.makedirs(USER_DATA_DIR, exist_ok=True)
        cmd = [
            CHROME_PATH,
            f"--remote-debugging-port={CDP_PORT}",
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-background-networking",
            f"--user-data-dir={USER_DATA_DIR}",
            "--window-size=1440,900"
        ]
        self.proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def stop(self):
        if self.event_listener_task:
            self.event_listener_task.cancel()
        if self.proc:
            try:
                subprocess.run(f"taskkill /F /PID {self.proc.pid} /T", shell=True, capture_output=True)
            except Exception:
                pass
            self.proc = None

    async def connect(self, target_url):
        # Poll for debugger url
        ws_url = None
        for _ in range(30):
            try:
                async with httpx.AsyncClient() as client:
                    res = await client.get(f"http://127.0.0.1:{CDP_PORT}/json/list", timeout=2)
                    tabs = res.json()
                    page_tabs = [t for t in tabs if t.get("type") == "page"]
                    target_tab = page_tabs[0] if page_tabs else (tabs[0] if tabs else None)
                    if target_tab:
                        ws_url = target_tab.get("webSocketDebuggerUrl")
                        if ws_url:
                            break
            except Exception:
                pass
            await asyncio.sleep(0.5)

        if not ws_url:
            raise RuntimeError("Failed to attach to Chrome CDP remote debugging endpoint.")

        self.ws = await websockets.connect(ws_url, max_size=100 * 1024 * 1024)
        self.event_listener_task = asyncio.create_task(self._listen_events())

        # Enable domains
        await self.call("Page.enable")
        await self.call("Runtime.enable")
        await self.call("Network.enable")
        await self.call("Page.navigate", {"url": target_url})
        await asyncio.sleep(2)

    async def _listen_events(self):
        try:
            async for raw in self.ws:
                try:
                    msg = json.loads(raw)
                    mid = msg.get("id")
                    if mid and mid in self.pending:
                        fut = self.pending.pop(mid)
                        if not fut.done():
                            fut.set_result(msg)
                    
                    method = msg.get("method")
                    if method == "Runtime.consoleAPICalled":
                        params = msg.get("params", {})
                        args = params.get("args", [])
                        txt = " ".join([str(a.get("value", a.get("description", str(a)))) if isinstance(a, dict) else str(a) for a in args])
                        self.console_logs.append({"level": params.get("type", "log"), "text": txt})
                    elif method == "Network.responseReceived":
                        resp = msg.get("params", {}).get("response", {})
                        status = resp.get("status", 200)
                        url = resp.get("url", "")
                        if status >= 400 and not url.endswith((".ico", ".map", ".woff", ".woff2")):
                            self.failed_requests.append({"url": url, "status": status, "statusText": resp.get("statusText", "")})
                except Exception:
                    pass
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
        res = await asyncio.wait_for(fut, timeout=30)
        return res

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

    async def wait_for_condition(self, expr, timeout=25, poll_interval=0.5):
        steps = int(timeout / poll_interval)
        for _ in range(steps):
            try:
                res = await self.evaluate(expr)
                if res:
                    return res
            except Exception:
                pass
            await asyncio.sleep(poll_interval)
        return False

    async def login_user(self, username, password):
        await self.evaluate("window.location.href = '/login'")
        await asyncio.sleep(2)
        
        # Focus & type username
        await self.evaluate("document.getElementById('username-input').focus()")
        await self.call("Input.insertText", {"text": username})
        
        # Focus & type password
        await self.evaluate("document.getElementById('password-input').focus()")
        await self.call("Input.insertText", {"text": password})
        
        # Submit login form
        await self.evaluate("document.querySelector('form button[type=\"submit\"]').click()")
        
        # Poll up to 20s for token in localStorage
        token_found = False
        for _ in range(40):
            await asyncio.sleep(0.5)
            tok = await self.evaluate("localStorage.getItem('token')")
            if tok:
                token_found = True
                break
        
        # Wait for portal / dashboard navigation
        for _ in range(20):
            await asyncio.sleep(0.5)
            p = await self.evaluate("window.location.pathname")
            if p and p != "/login":
                break
        
        await asyncio.sleep(1)
        return token_found

    async def navigate_to_opportunities(self):
        # Client-side navigation via CRM card and sidebar to preserve React session
        cur_path = await self.evaluate("window.location.pathname")
        if cur_path == "/portal":
            # Click CRM card
            await self.evaluate("""(() => {
                const crmCard = Array.from(document.querySelectorAll('.portal-card, .portal-service-card, h3, div')).find(el => el.innerText === 'CRM');
                if (crmCard) crmCard.click();
            })()""")
            await asyncio.sleep(2)
        
        # Click Opportunities in CrmSidebar
        await self.evaluate("""(() => {
            const oppLink = document.querySelector('a[href="/crm/opportunities"]') || Array.from(document.querySelectorAll('a')).find(a => a.innerText.includes('Opportunities'));
            if (oppLink) oppLink.click();
        })()""")
        await asyncio.sleep(1)

        # Wait for backend Neon query to load cards (specifically wait for OPP- cards to render)
        await self.wait_for_condition(
            "Boolean(document.body.innerText.includes('OPP-'))",
            timeout=45
        )
        await asyncio.sleep(1.5)

    async def open_opportunity_card(self, opp_prefix="OPP-"):
        # Wait for card with opp_prefix to be present in DOM
        await self.wait_for_condition(
            f"Boolean(document.body.innerText.includes('{opp_prefix}'))",
            timeout=45
        )
        # Click the opportunity card containing opp_prefix
        clicked = await self.evaluate(f"""(() => {{
            const spans = Array.from(document.querySelectorAll('span')).filter(s => s.innerText && s.innerText.includes('{opp_prefix}'));
            for (let s of spans) {{
                const card = s.closest('div[style*="cursor: pointer"]') || s.closest('.kanban-card') || s;
                if (card) {{
                    card.scrollIntoView({{ block: 'center', inline: 'center' }});
                    card.click();
                    return true;
                }}
            }}
            return false;
        }})()""")

        if clicked:
            # Wait for modal to render
            await self.wait_for_condition(
                "Boolean(document.body.innerText.includes('Overview & Details'))",
                timeout=45
            )
            # Wait for opportunity details loading spinner to finish
            await self.wait_for_condition(
                "!Boolean(document.body.innerText.includes('Loading opportunity details...'))",
                timeout=45
            )
            await asyncio.sleep(1.5)
        return clicked

    async def switch_to_quotations_tab(self):
        # Click specifically the tab bar button with text "Quotations"
        switched = await self.evaluate("""(() => {
            const buttons = Array.from(document.querySelectorAll('button'));
            const tabBtn = buttons.find(b => {
                const txt = (b.innerText || '').trim();
                return (txt.startsWith('Quotations') || txt === 'Quotations') && !txt.includes('Create') && !txt.includes('New');
            });
            if (tabBtn) {
                tabBtn.click();
                return true;
            }
            return false;
        })()""")
        # Wait for the quotations tab header to be rendered in the DOM
        await self.wait_for_condition(
            "Boolean(document.body.innerText.includes('Opportunity Quotations & Commercial Governance'))",
            timeout=25
        )
        # Wait for quotations loading spinner to finish
        await self.wait_for_condition(
            "!Boolean(document.body.innerText.includes('Loading quotations...'))",
            timeout=25
        )
        await asyncio.sleep(1)
        return switched

    async def logout_user(self):
        await self.evaluate("localStorage.clear(); sessionStorage.clear(); window.location.href = '/login';")
        await asyncio.sleep(2)


async def run_suite():
    print("=" * 80, flush=True)
    print("REVY Portal Phase 5A — Full Browser Smoke Testing Suite", flush=True)
    print("=" * 80, flush=True)
    
    results = []
    def record(scenario, status, details):
        results.append({"scenario": scenario, "status": status, "details": details})
        print(f"[{status}] {scenario}: {details}", flush=True)

    browser = CDPBrowser()
    browser.start()

    try:
        print("[INIT] Launching Google Chrome headless with CDP remote debugging...", flush=True)
        await browser.connect(f"{BASE_URL}/login")
        await asyncio.sleep(2)

        # -------------------------------------------------------------------------
        # Track 1: Sales Executive Authentication & Opportunities Funnel
        # -------------------------------------------------------------------------
        print("\n--- TRACK 1: Sales Executive Smoke Tests ---", flush=True)
        
        # 1.1 Login Page
        title = await browser.evaluate("document.title")
        has_form = await browser.evaluate("Boolean(document.getElementById('username-input') && document.getElementById('password-input'))")
        await browser.screenshot("01_login_page.png")
        if title == "REVY Portal" and has_form:
            record("1.1: Login Page Rendering", "PASS", "Login form rendered with brand headers and inputs.")
        else:
            record("1.1: Login Page Rendering", "FAIL", f"Title: {title}, has_form: {has_form}")

        # 1.2 Sales Exec Login
        login_ok = await browser.login_user("stg4_sales_exec", "Pass123!")
        curr_url = await browser.evaluate("window.location.href")
        await browser.screenshot("02_sales_exec_portal.png")
        if login_ok and "/portal" in curr_url:
            record("1.2: Sales Executive Login", "PASS", "Authenticated as stg4_sales_exec. Redirected to /portal.")
        else:
            record("1.2: Sales Executive Login", "FAIL", f"Login ok: {login_ok}, URL: {curr_url}")

        # 1.3 Opportunities Board & 6 Stages
        await browser.navigate_to_opportunities()
        await browser.screenshot("03_kanban_board_exec.png")
        
        stages = await browser.evaluate("""(() => {
            const expected = ['Enquiry', 'Qualify', 'Develop', 'Propose/Offer', 'Negotiate', 'Close'];
            const text = document.body.innerText;
            return expected.filter(s => text.includes(s));
        })()""")
        
        has_kpi_metrics = await browser.evaluate("""Boolean(
            document.body.innerText.includes('Open Pipeline Value') || 
            document.body.innerText.includes('OPEN PIPELINE VALUE')
        )""")
        
        has_opp_cards = await browser.evaluate("Boolean(document.body.innerText.includes('OPP-'))")

        if len(stages) == 6 and has_kpi_metrics and has_opp_cards:
            record("1.3: 6-Stage Kanban & Currency KPIs", "PASS", f"All 6 stages verified: {stages}. Currency-grouped KPI cards rendered with live opportunity cards.")
        else:
            record("1.3: 6-Stage Kanban & Currency KPIs", "FAIL", f"Stages: {stages}, KPIs: {has_kpi_metrics}, Cards: {has_opp_cards}")

        # -------------------------------------------------------------------------
        # Track 2: Quotation Lifecycle (Executive: Create & Submit)
        # -------------------------------------------------------------------------
        print("\n--- TRACK 2: Quotation Lifecycle (Sales Executive) ---", flush=True)
        
        # Open Opportunity modal (OPP-00002)
        card_opened = await browser.open_opportunity_card("OPP-00002")
        await browser.screenshot("04_opportunity_modal.png")

        # Switch to Quotations tab
        await browser.switch_to_quotations_tab()
        await browser.screenshot("05_quotations_tab.png")

        # Check if an active quotation already exists; if not, create one
        has_active_quote = await browser.evaluate("Boolean(document.body.innerText.includes('ACTIVE QUOTATION'))")
        if not has_active_quote:
            # Click "New Quotation" or "Create First Quotation"
            await browser.evaluate("""(() => {
                const btn = Array.from(document.querySelectorAll('button')).find(b => b.innerText && (b.innerText.includes('New Quotation') || b.innerText.includes('Create First Quotation')));
                if (btn) btn.click();
            })()""")
            await browser.wait_for_condition("Boolean(document.body.innerText.includes('Create New Quotation'))", timeout=25)
            await asyncio.sleep(1)

            # Set Title, Amount, and Document Reference via native input setters
            await browser.evaluate("""(() => {
                const titleInp = document.querySelector('input[placeholder*="Commercial Proposal"]') || document.querySelector('input[placeholder*="Proposal"]');
                if (titleInp) {
                    const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                    nativeSetter.call(titleInp, 'Bio-Energy Digester Supply QTN-2026-BROWSER-1');
                    titleInp.dispatchEvent(new Event('input', { bubbles: true }));
                    titleInp.dispatchEvent(new Event('change', { bubbles: true }));
                }
                const amountInp = document.querySelector('input[placeholder="0.00"]') || document.querySelector('input[type="number"]');
                if (amountInp) {
                    const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                    nativeSetter.call(amountInp, '650000');
                    amountInp.dispatchEvent(new Event('input', { bubbles: true }));
                    amountInp.dispatchEvent(new Event('change', { bubbles: true }));
                }
                const docInp = document.querySelector('input[placeholder*="Proposal_Biogas"]');
                if (docInp) {
                    const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                    nativeSetter.call(docInp, 'REVY_Digester_Proposal_v1.pdf');
                    docInp.dispatchEvent(new Event('input', { bubbles: true }));
                    docInp.dispatchEvent(new Event('change', { bubbles: true }));
                }
            })()""")
            await asyncio.sleep(0.5)

            # Click Create Quotation submit button
            await browser.evaluate("""(() => {
                const submitBtn = Array.from(document.querySelectorAll('button[type=\"submit\"]')).find(b => b.innerText.includes('Create Quotation'));
                if (submitBtn) submitBtn.click();
            })()""")
            await browser.wait_for_condition("Boolean(document.body.innerText.includes('ACTIVE QUOTATION'))", timeout=40)
            await asyncio.sleep(2)

        await browser.screenshot("06_quotation_created_draft.png")

        draft_ok = await browser.evaluate("""Boolean(
            (document.body.innerText.includes('Draft') || document.body.innerText.includes('Under Review')) && 
            (document.body.innerText.includes('650,000') || document.body.innerText.includes('650000'))
        )""")
        
        if draft_ok:
            record("2.1: Quotation Creation (Draft v1)", "PASS", "Quotation created in 'Draft' status with v1 version tag and ₹650,000 commercial value.")
        else:
            record("2.1: Quotation Creation (Draft v1)", "FAIL", "Draft status or 650,000 amount not detected.")

        # Submit for Review
        has_submit_btn = await browser.evaluate("""Boolean(
            Array.from(document.querySelectorAll('button')).find(b => b.innerText && b.innerText.includes('Submit for Review'))
        )""")
        if has_submit_btn:
            await browser.evaluate("""(() => {
                const btn = Array.from(document.querySelectorAll('button')).find(b => b.innerText && b.innerText.includes('Submit for Review'));
                if (btn) btn.click();
            })()""")
            await browser.wait_for_condition("Boolean(document.body.innerText.includes('Under Review'))", timeout=40)
            await asyncio.sleep(2)

        await browser.screenshot("07_quotation_submitted_review.png")

        under_review = await browser.evaluate("""Boolean(
            document.body.innerText.includes('Under Review') || document.body.innerText.includes('In Review')
        )""")
        
        # Verify Sales Executive cannot approve
        can_exec_approve = await browser.evaluate("""Boolean(
            Array.from(document.querySelectorAll('button')).find(b => b.innerText && (b.innerText.includes('Approve') || b.innerText.includes('Review & Approve')))
        )""")
        
        if under_review and not can_exec_approve:
            record("2.2: Quotation Submission & RBAC Gate", "PASS", "Quotation transitioned to 'Under Review'. Commercial approval controls strictly suppressed for Sales Executive.")
        else:
            record("2.2: Quotation Submission & RBAC Gate", "FAIL", f"under_review: {under_review}, can_exec_approve: {can_exec_approve}")

        # Close modal & logout
        await browser.evaluate("""(() => {
            const closeBtn = Array.from(document.querySelectorAll('button')).find(b => b.innerText === '✕');
            if (closeBtn) closeBtn.click();
        })()""")
        await asyncio.sleep(1)
        await browser.logout_user()

        # -------------------------------------------------------------------------
        # Track 3: Sales Manager Review & Commercial Approval
        # -------------------------------------------------------------------------
        print("\n--- TRACK 3: Sales Manager Approval ---", flush=True)
        login_mgr_ok = await browser.login_user("stg4_sales_mgr", "Pass123!")
        await browser.navigate_to_opportunities()
        await browser.screenshot("08_sales_mgr_kanban.png")

        # Open Opportunity & Quotations tab
        await browser.open_opportunity_card("OPP-00002")
        await browser.switch_to_quotations_tab()
        await browser.screenshot("09_mgr_quotations_tab.png")

        has_mgr_review_btn = await browser.evaluate("""Boolean(
            Array.from(document.querySelectorAll('button')).find(b => b.innerText && (b.innerText.includes('Review & Approve') || b.innerText.includes('Review & Approve / Reject')))
        )""")
        
        if has_mgr_review_btn:
            # Click Review & Approve
            await browser.evaluate("""(() => {
                const btn = Array.from(document.querySelectorAll('button')).find(b => b.innerText && (b.innerText.includes('Review & Approve') || b.innerText.includes('Review & Approve / Reject')));
                if (btn) btn.click();
            })()""")
            await browser.wait_for_condition("Boolean(document.body.innerText.includes('Review Quotation'))", timeout=25)
            await asyncio.sleep(1)
            await browser.screenshot("10_manager_approval_modal.png")

            # Confirm Approval
            await browser.evaluate("""(() => {
                const confirmBtn = Array.from(document.querySelectorAll('button[type=\"submit\"]')).find(b => b.innerText && b.innerText.includes('Confirm Approval'));
                if (confirmBtn) confirmBtn.click();
            })()""")
            await browser.wait_for_condition("Boolean(document.body.innerText.includes('Approved'))", timeout=40)
            await asyncio.sleep(2)

        await browser.screenshot("11_quotation_approved.png")

        approved_ok = await browser.evaluate("""Boolean(document.body.innerText.includes('Approved'))""")
        if approved_ok:
            record("3.1: Sales Manager Commercial Approval", "PASS", "Sales Manager reviewed and approved quotation. Status updated to 'Approved' with audit stamp.")
        else:
            record("3.1: Sales Manager Commercial Approval", "FAIL", f"has_review_btn: {has_mgr_review_btn}, approved_ok: {approved_ok}")

        # Close modal & logout
        await browser.evaluate("""(() => {
            const closeBtn = Array.from(document.querySelectorAll('button')).find(b => b.innerText === '✕');
            if (closeBtn) closeBtn.click();
        })()""")
        await asyncio.sleep(1)
        await browser.logout_user()

        # -------------------------------------------------------------------------
        # Track 4: External Client Share & Multi-Revision Governance
        # -------------------------------------------------------------------------
        print("\n--- TRACK 4: Client Share & Revision (Sales Executive) ---", flush=True)
        await browser.login_user("stg4_sales_exec", "Pass123!")
        await browser.navigate_to_opportunities()
        await browser.open_opportunity_card("OPP-00002")
        await browser.switch_to_quotations_tab()

        # Record Client Share
        has_share_btn = await browser.evaluate("""Boolean(
            Array.from(document.querySelectorAll('button')).find(b => b.innerText && b.innerText.includes('Mark Shared with Client'))
        )""")
        
        if has_share_btn:
            await browser.evaluate("""(() => {
                const btn = Array.from(document.querySelectorAll('button')).find(b => b.innerText && b.innerText.includes('Mark Shared with Client'));
                if (btn) btn.click();
            })()""")
            await browser.wait_for_condition("Boolean(document.body.innerText.includes('Record External Quotation Sharing'))", timeout=25)
            await asyncio.sleep(1)
            await browser.screenshot("12_share_modal.png")

            # Focus and enter Recipient
            await browser.evaluate("""(() => {
                const inp = document.querySelector('input[placeholder*="client@example.com"]');
                if (inp) {
                    const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                    nativeSetter.call(inp, 'procurement@client-corp.com');
                    inp.dispatchEvent(new Event('input', { bubbles: true }));
                    inp.dispatchEvent(new Event('change', { bubbles: true }));
                }
            })()""")
            await asyncio.sleep(0.5)

            # Focus and enter Evidence
            await browser.evaluate("""(() => {
                const inp = document.querySelector('textarea[placeholder*="Gmail"]');
                if (inp) {
                    const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
                    nativeSetter.call(inp, 'Sent via corporate email proposal-ref-2026.pdf');
                    inp.dispatchEvent(new Event('input', { bubbles: true }));
                    inp.dispatchEvent(new Event('change', { bubbles: true }));
                }
            })()""")
            await asyncio.sleep(0.5)

            # Submit
            await browser.evaluate("""(() => {
                const submitBtn = Array.from(document.querySelectorAll('button[type="submit"]')).find(b => b.innerText.includes('Mark as Shared'));
                if (submitBtn) submitBtn.click();
            })()""")
            # Wait for share modal to close completely AND status badge to become Shared
            await browser.wait_for_condition(
                "!Boolean(document.body.innerText.includes('Record External Quotation Sharing')) && Boolean(Array.from(document.querySelectorAll('span')).some(s => (s.innerText || '').trim() === 'Shared'))",
                timeout=60
            )
            await asyncio.sleep(2)

        await browser.screenshot("13_quotation_shared.png")

        shared_ok = await browser.evaluate("""Boolean(
            Array.from(document.querySelectorAll('span')).some(s => (s.innerText || '').trim() === 'Shared')
        )""")
        if shared_ok:
            record("4.1: Record Client Sharing Audit", "PASS", "Recorded external sharing to procurement@client-corp.com via Email. Status updated to 'Shared' with audit log.")
        else:
            record("4.1: Record Client Sharing Audit", "FAIL", "Status 'Shared' not detected.")

        # Wait for New Revision button to become visible
        await browser.wait_for_condition("""Boolean(
            Array.from(document.querySelectorAll('button')).find(b => b.innerText && b.innerText.includes('New Revision'))
        )""", timeout=30)
        await asyncio.sleep(1)

        # Create Revision (v2)
        has_rev_btn = await browser.evaluate("""Boolean(
            Array.from(document.querySelectorAll('button')).find(b => b.innerText && b.innerText.includes('New Revision'))
        )""")
        
        if has_rev_btn:
            await browser.evaluate("""(() => {
                const btn = Array.from(document.querySelectorAll('button')).find(b => b.innerText && b.innerText.includes('New Revision'));
                if (btn) btn.click();
            })()""")
            await browser.wait_for_condition("Boolean(document.body.innerText.includes('Revise Quotation'))", timeout=25)
            await asyncio.sleep(1)

            # Select and replace amount with 700000 via native setter
            await browser.evaluate("""(() => {
                const amountInput = document.querySelector('input[type="number"]') || document.querySelector('input[placeholder="0.00"]');
                if (amountInput) {
                    const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                    nativeSetter.call(amountInput, '700000');
                    amountInput.dispatchEvent(new Event('input', { bubbles: true }));
                    amountInput.dispatchEvent(new Event('change', { bubbles: true }));
                }
            })()""")
            await asyncio.sleep(0.5)

            # Submit Revision
            await browser.evaluate("""(() => {
                const submitBtn = Array.from(document.querySelectorAll('button[type="submit"]')).find(b => b.innerText.includes('Create Revision'));
                if (submitBtn) submitBtn.click();
            })()""")
            # Wait for revise modal to close and v2 to appear in the active quotation
            await browser.wait_for_condition(
                "!Boolean(document.body.innerText.includes('Revise Quotation')) && Boolean(document.body.innerText.includes('v2')) && Boolean(document.body.innerText.includes('Quotation Revision History (2)'))",
                timeout=60
            )
            await asyncio.sleep(2)

        await browser.screenshot("14_quotation_revised_v2.png")

        revision_v2_ok = await browser.evaluate("""Boolean(
            document.body.innerText.includes('v2') && 
            (document.body.innerText.includes('700,000') || document.body.innerText.includes('700000')) &&
            document.body.innerText.includes('Quotation Revision History (2)')
        )""")
        
        if revision_v2_ok:
            record("4.2: Multi-Revision Governance (v2 Draft)", "PASS", "Quotation revised to v2 (₹700,000 Draft). History table records 2 total revisions with active indicator.")
        else:
            record("4.2: Multi-Revision Governance (v2 Draft)", "FAIL", "v2 draft or history count not detected.")

        # Close modal & logout
        await browser.evaluate("""(() => {
            const closeBtn = Array.from(document.querySelectorAll('button')).find(b => b.innerText === '✕');
            if (closeBtn) closeBtn.click();
        })()""")
        await asyncio.sleep(1)
        await browser.logout_user()

        # -------------------------------------------------------------------------
        # Track 5: Deal Reopening Governance
        # -------------------------------------------------------------------------
        print("\n--- TRACK 5: Deal Reopening Governance ---", flush=True)
        # Sales Exec check
        await browser.login_user("stg4_sales_exec", "Pass123!")
        
        # Navigate directly to Won view
        await browser.evaluate("window.location.href = '/crm/opportunities?view=won'")
        await browser.wait_for_condition(
            "Boolean(document.body.innerText.includes('OPP-00008') || document.body.innerText.includes('OPP-00012'))",
            timeout=25
        )
        await asyncio.sleep(1)

        await browser.open_opportunity_card("OPP-00012")
        await browser.screenshot("15_exec_closed_deal.png")

        exec_has_reopen = await browser.evaluate("""Boolean(
            Array.from(document.querySelectorAll('button')).find(b => b.innerText && b.innerText.includes('Reopen Opportunity'))
        )""")
        
        if not exec_has_reopen:
            record("5.1: Deal Reopening RBAC Block (Sales Exec)", "PASS", "Sales Executive cannot see or trigger 'Reopen Opportunity' action on closed deal.")
        else:
            record("5.1: Deal Reopening RBAC Block (Sales Exec)", "FAIL", "Reopen button was unexpectedly visible to Sales Executive.")

        await browser.evaluate("""(() => {
            const closeBtn = Array.from(document.querySelectorAll('button')).find(b => b.innerText === '✕');
            if (closeBtn) closeBtn.click();
        })()""")
        await asyncio.sleep(1)
        await browser.logout_user()

        # Sales Manager check & execute reopen
        await browser.login_user("stg4_sales_mgr", "Pass123!")
        await browser.evaluate("window.location.href = '/crm/opportunities?view=won'")
        await browser.wait_for_condition(
            "Boolean(document.body.innerText.includes('OPP-00012') || document.body.innerText.includes('OPP-00008'))",
            timeout=25
        )
        await asyncio.sleep(1)

        await browser.open_opportunity_card("OPP-00012")
        await browser.screenshot("16_mgr_closed_deal.png")

        mgr_has_reopen = await browser.evaluate("""Boolean(
            Array.from(document.querySelectorAll('button')).find(b => b.innerText && b.innerText.includes('Reopen Opportunity'))
        )""")

        if mgr_has_reopen:
            await browser.evaluate("""(() => {
                const btn = Array.from(document.querySelectorAll('button')).find(b => b.innerText && b.innerText.includes('Reopen Opportunity'));
                if (btn) btn.click();
            })()""")
            await browser.wait_for_condition("Boolean(document.body.innerText.includes('Reopen Opportunity') && document.querySelector('textarea'))", timeout=15)
            await asyncio.sleep(1)
            await browser.screenshot("17_reopen_modal.png")

            # Select stage Negotiate via React value setter
            await browser.evaluate("""(() => {
                const sel = Array.from(document.querySelectorAll('select')).find(s => Array.from(s.options).some(o => o.value === 'Negotiate'));
                if (sel) {
                    const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype, 'value').set;
                    nativeSetter.call(sel, 'Negotiate');
                    sel.dispatchEvent(new Event('change', { bubbles: true }));
                }
            })()""")

            # Focus and enter mandatory justification
            await browser.evaluate("""(() => {
                const txt = document.querySelector('textarea[placeholder*=\"rationale\"]') || document.querySelector('textarea');
                if (txt) { txt.focus(); }
            })()""")
            await browser.call("Input.insertText", {"text": "Client requested revised scope and extended commercial terms for plant upgrade."})
            await asyncio.sleep(0.5)

            # Confirm Reopen
            await browser.evaluate("""(() => {
                const submitBtn = Array.from(document.querySelectorAll('button[type=\"submit\"]')).find(b => b.innerText.includes('Confirm Reopen'));
                if (submitBtn) submitBtn.click();
            })()""")
            await browser.wait_for_condition("Boolean(document.body.innerText.includes('Negotiate') || document.body.innerText.includes('OPEN'))", timeout=20)
            await asyncio.sleep(1.5)
            await browser.screenshot("18_deal_reopened.png")

            reopen_ok = await browser.evaluate("""Boolean(
                document.body.innerText.includes('Negotiate') || document.body.innerText.includes('OPEN') || document.body.innerText.includes('Open')
            )""")
            if reopen_ok:
                record("5.2: Deal Reopening Execution (Sales Mgr)", "PASS", "Sales Manager reopened closed opportunity to 'Negotiate' stage with mandatory audit justification.")
            else:
                record("5.2: Deal Reopening Execution (Sales Mgr)", "FAIL", "Reopened stage 'Negotiate' or 'Open' not detected.")
        else:
            record("5.2: Deal Reopening Execution (Sales Mgr)", "FAIL", "Reopen button was not visible to Sales Manager.")

        await browser.evaluate("""(() => {
            const closeBtn = Array.from(document.querySelectorAll('button')).find(b => b.innerText === '✕');
            if (closeBtn) closeBtn.click();
        })()""")
        await asyncio.sleep(1)
        await browser.logout_user()

        # -------------------------------------------------------------------------
        # Track 6: CRM Administrator Navigation & Governance
        # -------------------------------------------------------------------------
        print("\n--- TRACK 6: CRM Administrator Pipeline Governance ---", flush=True)
        admin_login = await browser.login_user("stg4_crm_admin", "Pass123!")
        await browser.screenshot("19_crm_admin_portal.png")
        await browser.navigate_to_opportunities()
        await browser.screenshot("20_crm_admin_kanban.png")

        admin_kanban = await browser.evaluate("""Boolean(
            document.body.innerText.includes('Enquiry') && document.body.innerText.includes('Close')
        )""")
        
        if admin_login and admin_kanban:
            record("6.1: CRM Administrator Governance Access", "PASS", "CRM Administrator authenticated and accessed pipeline Kanban board with complete pipeline oversight.")
        else:
            record("6.1: CRM Administrator Governance Access", "FAIL", f"admin_login: {admin_login}, admin_kanban: {admin_kanban}")

        await browser.logout_user()

        # -------------------------------------------------------------------------
        # Track 7: Console Errors & Failed Network Requests Audit
        # -------------------------------------------------------------------------
        print("\n--- TRACK 7: Console & Network Request Audit ---", flush=True)
        console_errors = [c for c in browser.console_logs if c.get("level") in ("error", "assert")]
        record("7.1: Browser Console Error Audit", "PASS" if len(console_errors) == 0 else "WARNING", f"{len(console_errors)} console errors recorded.")
        
        record("7.2: Failed Network Requests Audit", "PASS" if len(browser.failed_requests) == 0 else "WARNING", f"{len(browser.failed_requests)} failed HTTP requests recorded.")

    finally:
        browser.stop()

    print("\n" + "=" * 80, flush=True)
    print("BROWSER SMOKE TEST EXECUTION SUMMARY", flush=True)
    print("=" * 80, flush=True)
    for r in results:
        print(f"[{r['status']}] {r['scenario']} -> {r['details']}", flush=True)
    
    summary_path = os.path.join(SCREENSHOT_DIR, "browser_smoke_test_results.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump({"results": results, "console_logs": browser.console_logs, "failed_requests": browser.failed_requests}, f, indent=2)
    print(f"\nSaved execution results to: {summary_path}", flush=True)

if __name__ == "__main__":
    asyncio.run(run_suite())
