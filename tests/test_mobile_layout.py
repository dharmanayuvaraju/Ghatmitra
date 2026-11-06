import asyncio
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

import uvicorn
import websockets
from app.main import app

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
UVICORN_PORT = 8009
CDP_PORT = 9229


def start_uvicorn():
    uvicorn.run(app, host="127.0.0.1", port=UVICORN_PORT, log_level="error")


async def run_cdp_tests():
    # 1. Start Uvicorn
    t = threading.Thread(target=start_uvicorn, daemon=True)
    t.start()
    time.sleep(1.2)

    # 2. Start Chrome
    tmp_dir = tempfile.mkdtemp()
    cmd = [
        CHROME_PATH,
        "--headless=new",
        f"--remote-debugging-port={CDP_PORT}",
        f"--user-data-dir={tmp_dir}",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--remote-allow-origins=*",
        "--no-first-run",
        "--no-default-browser-check",
    ]
    proc = subprocess.Popen(cmd)
    time.sleep(1.5)

    try:
        # Get target websocket URL
        req = urllib.request.urlopen(f"http://127.0.0.1:{CDP_PORT}/json/version")
        ver_data = json.loads(req.read())
        ws_url = ver_data["webSocketDebuggerUrl"]

        async with websockets.connect(ws_url) as ws:
            msg_id = 0

            async def send_cmd(method, params=None):
                nonlocal msg_id
                msg_id += 1
                payload = {"id": msg_id, "method": method, "params": params or {}}
                await ws.send(json.dumps(payload))
                while True:
                    res = json.loads(await ws.recv())
                    if res.get("id") == msg_id:
                        return res.get("result", {})

            # Create new page target
            target_res = await send_cmd("Target.createTarget", {"url": f"http://127.0.0.1:{UVICORN_PORT}/"})
            target_id = target_res["targetId"]

            # Connect to page target
            session_res = await send_cmd("Target.attachToTarget", {"targetId": target_id, "flatten": True})
            session_id = session_res["sessionId"]

            async def page_cmd(method, params=None):
                nonlocal msg_id
                msg_id += 1
                payload = {"id": msg_id, "sessionId": session_id, "method": method, "params": params or {}}
                await ws.send(json.dumps(payload))
                while True:
                    res = json.loads(await ws.recv())
                    if res.get("id") == msg_id:
                        return res.get("result", {})

            await page_cmd("Page.enable")
            await page_cmd("DOM.enable")

            viewports = [360, 390, 412]
            routes = ["#home", "#guard", "#field", "#works", "#assets", "#vendors", "#alerts", "#report"]

            for w in viewports:
                print(f"\n=================== TESTING VIEWPORT {w}px ===================")
                await page_cmd("Emulation.setDeviceMetricsOverride", {
                    "width": w,
                    "height": 800,
                    "deviceScaleFactor": 2,
                    "mobile": True
                })

                # Navigate to root
                await page_cmd("Page.navigate", {"url": f"http://127.0.0.1:{UVICORN_PORT}/"})
                await asyncio.sleep(1.0)

                for route in routes:
                    # Switch hash
                    eval_res = await page_cmd("Runtime.evaluate", {
                        "expression": f"window.location.hash = '{route}';"
                    })
                    await asyncio.sleep(0.3)

                    # Check layout width
                    res = await page_cmd("Runtime.evaluate", {
                        "expression": """(() => {
                            const winW = window.innerWidth;
                            const docW = document.documentElement.scrollWidth;
                            const bodyW = document.body.scrollWidth;
                            const overflowing = [];
                            document.querySelectorAll('*').forEach(el => {
                                if (el.scrollWidth > winW) {
                                    overflowing.push({
                                        tag: el.tagName,
                                        id: el.id,
                                        cls: el.className.toString().slice(0, 40),
                                        scrollWidth: el.scrollWidth
                                    });
                                }
                            });
                            return JSON.stringify({
                                winW,
                                docW,
                                bodyW,
                                ok: docW <= winW && bodyW <= winW,
                                overflowing
                            });
                        })()"""
                    })
                    val = json.loads(res.get("result", {}).get("value", "{}"))
                    ok = val.get("ok", False)
                    doc_w = val.get("docW")
                    win_w = val.get("winW")
                    overflowing = val.get("overflowing", [])

                    status_str = "PASS" if ok else "FAIL"
                    print(f"[{status_str}] Viewport {w}px | Route {route:<8} | docWidth={doc_w}px, winWidth={win_w}px | Overflow items: {len(overflowing)}")
                    if not ok:
                        for item in overflowing[:5]:
                            print(f"    -> {item}")
                        assert ok, f"Overflow detected at viewport {w}px on route {route}: docW={doc_w} > winW={win_w}"

            # Test Nav badges and Demo Mode step 1
            print("\n=================== TESTING NAV BADGES & DEMO MODE STEP 1 ===================")
            badge_res = await page_cmd("Runtime.evaluate", {
                "expression": """(() => {
                    const guardBadge = document.getElementById('nav-badge-guard');
                    const worksBadge = document.getElementById('nav-badge-works');
                    const assetsBadge = document.getElementById('nav-badge-assets');
                    const alertsBadge = document.getElementById('nav-badge-alerts');
                    const vendorsBadge = document.getElementById('nav-badge-vendors');
                    const mobGuard = document.getElementById('mob-badge-guard');
                    const mobWorks = document.getElementById('mob-badge-works');
                    const mobAssets = document.getElementById('mob-badge-assets');
                    return JSON.stringify({
                        guardBadge: guardBadge ? guardBadge.innerText : null,
                        worksBadge: worksBadge ? worksBadge.innerText : null,
                        assetsBadge: assetsBadge ? assetsBadge.innerText : null,
                        alertsBadge: alertsBadge ? alertsBadge.innerText : null,
                        vendorsBadge: vendorsBadge ? vendorsBadge.innerText : null,
                        mobGuard: mobGuard ? mobGuard.innerText : null,
                        mobWorks: mobWorks ? mobWorks.innerText : null,
                        mobAssets: mobAssets ? mobAssets.innerText : null,
                    });
                })()"""
            })
            badges = json.loads(badge_res.get("result", {}).get("value", "{}"))
            print("Badges loaded:", badges)
            assert badges["worksBadge"] is not None and badges["worksBadge"] != "undefined"
            assert badges["assetsBadge"] is not None and badges["assetsBadge"] != "undefined"

            # Test Demo mode step 1 dynamic text
            await page_cmd("Runtime.evaluate", {"expression": "startDemoMode();"})
            await asyncio.sleep(0.6)
            demo_text_res = await page_cmd("Runtime.evaluate", {
                "expression": "document.getElementById('demo-step-text').innerText"
            })
            demo_text = demo_text_res.get("result", {}).get("value", "")
            print("Demo step 1 text:", demo_text)
            assert "Works across 5 Ghats" in demo_text
            assert "Delayed Works" in demo_text
            assert "Cr of Budget at Risk" in demo_text

            print("\nALL MOBILE LAYOUT TESTS PASSED WITH 0 OVERFLOWS!")

    finally:
        proc.terminate()


if __name__ == "__main__":
    asyncio.run(run_cdp_tests())
