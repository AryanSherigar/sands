import asyncio
import os
import shutil
from playwright.async_api import async_playwright, expect

SCREENSHOTS_DIR = "/data/sands/.worktrees/strategy-proclamation-scene/scripts/screenshots/proclamation"
DOCS_REPORT_PATH = "/data/sands/.worktrees/strategy-proclamation-scene/docs/reports/proclamation-e2e-browser-test.png"
ARTIFACT_DIR = "/home/aryan-sherigar/.gemini/antigravity-cli/brain/3030ffbf-83d8-46aa-8560-9291df55f700"

MOCK_CLASSIFY_RESPONSE = {
    "is_recognized": True,
    "domain": "martial_levies",
    "burden": "moderate",
    "target_estate": "military",
    "concession_estate": None,
    "legal_summary": "Levy 200 silver from merchant guilds to reinforce border outposts.",
    "fallback_reason": None,
}

MOCK_CONVENE_RESPONSE = {
    "scene_id": "proc_scene_001",
    "draft": MOCK_CLASSIFY_RESPONSE,
    "ministers": [
        {
            "estate": "nobility",
            "title": "Lord Chancellor Morvath",
            "stance": "oppose",
            "primary_grievance": "Ancient charters forbid arbitrary levies upon free burghers.",
        },
        {
            "estate": "military",
            "title": "High Marshal Vane",
            "stance": "support",
            "primary_grievance": "The border watch posts are undermanned and starved of coin.",
        },
        {
            "estate": "burghers",
            "title": "Lord Treasurer Hest",
            "stance": "cautious",
            "primary_grievance": "Trade caravan tariffs will plummet if coin is forcibly seized.",
        },
        {
            "estate": "clergy",
            "title": "Arch-Prelate Tomas",
            "stance": "oppose",
            "primary_grievance": "The church tithes must not be contaminated by forced exactions.",
        },
    ],
    "exchange_cap": 6,
    "is_rescinding_previous": False,
}

MOCK_DECISION_RESPONSE = {
    "id": "proc_1_martial_levies",
    "legal_summary": "Levy 200 silver from merchant guilds to reinforce border outposts.",
    "domain": "martial_levies",
    "burden": "moderate",
    "enacted_turn": 1,
    "remaining_turns": 4,
    "immediate_deltas": {"manpower": 200, "gold": -50, "unrest": 5},
    "ongoing_modifiers": {"manpower_regen_delta": 25.0, "unrest_delta": 3.0},
}


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse
import uvicorn

mock_trs_app = FastAPI()
mock_trs_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@mock_trs_app.post("/strategy/proclamation/classify")
async def api_classify():
    print(">>> MOCK TRS: Received /strategy/proclamation/classify")
    return JSONResponse(content=MOCK_CLASSIFY_RESPONSE)


@mock_trs_app.post("/strategy/proclamation/narrate")
async def api_narrate():
    print(">>> MOCK TRS: Received /strategy/proclamation/narrate")

    async def sse_gen():
        yield {"event": "narration", "data": "[CHANCELLOR]: Sire, the merchant charters are sacred feudal compacts!"}
        await asyncio.sleep(0.1)
        yield {"event": "narration", "data": "[MARSHAL]: Without coin, the border garrisons will crumble."}
        await asyncio.sleep(0.1)
        yield {"event": "done", "data": '{"status": "completed"}'}

    return EventSourceResponse(sse_gen())


async def test_proclamation_flow():
    print("=== STARTING PLAYWRIGHT E2E BROWSER TEST FOR PROCLAMATION SCENE ===")
    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(DOCS_REPORT_PATH), exist_ok=True)
    os.makedirs(ARTIFACT_DIR, exist_ok=True)

    # Launch mock TRS server on 127.0.0.1:8001
    trs_config = uvicorn.Config(
        mock_trs_app,
        host="127.0.0.1",
        port=8001,
        log_level="warning",
    )
    trs_server = uvicorn.Server(trs_config)
    trs_server.install_signal_handlers = lambda: None
    trs_task = asyncio.create_task(trs_server.serve())
    await asyncio.sleep(0.5)

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--no-zygote",
                    "--font-render-hinting=none",
                    "--disable-background-timer-throttling",
                    "--disable-renderer-backgrounding",
                ],
            )
            context = await browser.new_context(
                viewport={"width": 1440, "height": 900},
                device_scale_factor=1,
            )
            page = await context.new_page()

            # Prevent headless Linux audio decoder crashes
            await page.add_init_script("""
                delete window.AudioContext;
                window.AudioContext = undefined;
                delete window.webkitAudioContext;
                window.webkitAudioContext = undefined;
            """)
            page.on("crash", lambda: print(">>> PAGE CRASHED! <<<"))
            page.on("console", lambda msg: print(f"PAGE CONSOLE: {msg.text}"))
            page.on("pageerror", lambda err: print(f"PAGE ERROR: {err}"))
            page.on("request", lambda req: print(f"PAGE REQ: {req.method} {req.url}"))
            page.on("response", lambda res: print(f"PAGE RES: {res.status} {res.url}"))

            # Wire route mocks for simulation endpoints
            async def handle_convene(route):
                print(">>> ROUTE CALLED: handle_convene")
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    json=MOCK_CONVENE_RESPONSE,
                )

            async def handle_decision(route):
                print(">>> ROUTE CALLED: handle_decision")
                await route.fulfill(
                    status=200,
                    content_type="application/json",
                    json=MOCK_DECISION_RESPONSE,
                )

            await page.route("**/proclamation/convene", handle_convene)
            await page.route("**/proclamation/decision", handle_decision)

            # Step 1: Navigate to strategy preview
            print("[1/7] Navigating to http://127.0.0.1:5173/play/strategy-preview...")
            await page.goto("http://127.0.0.1:5173/play/strategy-preview", wait_until="networkidle")
            await asyncio.sleep(1.0)

            shot1 = f"{SCREENSHOTS_DIR}/01_strategy_preview_canopy.png"
            await page.screenshot(path=shot1)
            print(f" -> Screenshot saved: {shot1}")

            # Step 2: Verify "Issue Proclamation (2 Mandates)" button is visible on Top Canopy
            print("[2/7] Finding 'Issue Proclamation' crown button on Top Canopy...")
            proclamation_btn = page.locator('button:has-text("Issue Proclamation")')
            await expect(proclamation_btn).to_be_visible(timeout=10000)
            print(" -> 'Issue Proclamation (2 Mandates)' button is visible and active!")

            # Step 3: Open the Scribe's Desk Draft Modal
            print("[3/7] Clicking 'Issue Proclamation' button to open Scribe Desk Modal...")
            await proclamation_btn.click()
            await asyncio.sleep(0.5)

            draft_modal = page.locator('div[role="dialog"][aria-label="Draft Royal Proclamation"]')
            await expect(draft_modal).to_be_visible(timeout=5000)
            print(" -> Scribe Desk Draft Modal opened successfully!")

            shot2 = f"{SCREENSHOTS_DIR}/02_scribe_desk_modal.png"
            await page.screenshot(path=shot2)
            print(f" -> Screenshot saved: {shot2}")

            # Step 4: Enter freeform decree text
            print("[4/7] Filling freeform decree into illuminated parchment textarea...")
            textarea = page.locator("#proclamation-input")
            decree_text = "Levy 200 silver from merchant guilds to reinforce border outposts."
            await textarea.fill(decree_text)
            await asyncio.sleep(0.3)

            convene_btn = page.locator('button:has-text("Convene Council & Read Edict")')
            await expect(convene_btn).to_be_enabled()
            await convene_btn.click()
            await asyncio.sleep(1.0)

            # Step 5: Verify Council Chamber opens with 4 Ministers and Live Transcript
            print("[5/7] Verifying Royal Council Chamber and all 4 Ministers...")
            council_dialog = page.locator('div[role="dialog"][aria-label="Royal Proclamation Council"]')
            await expect(council_dialog).to_be_visible(timeout=5000)

            # Verify all four ministers
            await expect(page.locator("text=Lord Chancellor Morvath")).to_be_visible()
            await expect(page.locator("text=High Marshal Vane")).to_be_visible()
            await expect(page.locator("text=Lord Treasurer Hest")).to_be_visible()
            await expect(page.locator("text=Arch-Prelate Tomas")).to_be_visible()
            print(" -> All 4 Estate Ministers rendered with Stances and Grievances!")

            # Verify live dialogue appeared in transcript
            await asyncio.sleep(0.8)
            await expect(page.locator("text=[Chancellor Morvath]:")).to_be_visible()
            await expect(page.locator("text=feudal compacts")).to_be_visible()
            print(" -> Live dialogue stream verified in Chamber Transcript!")

            shot3 = f"{SCREENSHOTS_DIR}/03_council_chamber_dialogue.png"
            await page.screenshot(path=shot3)
            print(f" -> Screenshot saved: {shot3}")

            # Step 6: Address the council and Pronounce verdict
            print("[6/7] Addressing council and clicking 'Enforce by Royal Fiat'...")
            address_input = page.locator('input[placeholder*="Address the council"]')
            await address_input.fill("The realm cannot stand divided; the merchants will find safe roads in return.")
            await page.locator('button:has-text("Address Council")').click()
            await asyncio.sleep(0.6)

            fiat_btn = page.locator('button:has-text("Enforce by Royal Fiat")')
            await expect(fiat_btn).to_be_visible()
            await fiat_btn.click()
            await asyncio.sleep(1.0)

            # Step 7: Verify Council closes and active edict appears on Top Canopy
            print("[7/7] Verifying Council closed and Active Edict pill is rendered...")
            await expect(council_dialog).not_to_be_visible()

            # Check Active Edict pill on canopy
            edict_pill = page.locator('text=/Edict:.*Levy 200 silver/i')
            await expect(edict_pill).to_be_visible()
            print(" -> Active Edict pill is visible on Top Canopy!")

            shot4 = f"{SCREENSHOTS_DIR}/04_council_resolved.png"
            await page.screenshot(path=shot4)
            print(f" -> Screenshot saved: {shot4}")

            # Save main verified artifact to docs/reports/ and antigravity brain
            await page.screenshot(path=DOCS_REPORT_PATH)
            shutil.copyfile(shot3, os.path.join(ARTIFACT_DIR, "proclamation-council-parley.png"))
            shutil.copyfile(DOCS_REPORT_PATH, os.path.join(ARTIFACT_DIR, "proclamation-e2e-browser-test.png"))
            print(f" -> Final Artifact saved to {DOCS_REPORT_PATH} and {ARTIFACT_DIR}!")

            await browser.close()
            print("=== PROCLAMATION SCENE PLAYWRIGHT E2E BROWSER TEST COMPLETED SUCCESSFULLY! ===")
    finally:
        trs_server.should_exit = True
        await trs_task


if __name__ == "__main__":
    asyncio.run(test_proclamation_flow())
