"""Browser check of the strategy letter flow against a real playthrough.

Needs a running stack and a playthrough that has a letter armed (letters are
opt-in per scenario and need an authored grudge or an earlier negotiation).

    LETTER_PLAYTHROUGH_URL=http://127.0.0.1:5173/play/<playthrough-id> \
    LETTER_STORAGE_STATE=/path/to/signed-in-state.json \
    python scripts/test_letter_scenario_playwright.py

LETTER_STORAGE_STATE is a Playwright storage_state file saved from a signed-in
session. LETTER_SCREENSHOTS_DIR defaults to scripts/screenshots/letter.
"""

import asyncio
import os
import re
import sys
from pathlib import Path

from playwright.async_api import Page, async_playwright, expect

ENV_URL = "LETTER_PLAYTHROUGH_URL"
ENV_STORAGE_STATE = "LETTER_STORAGE_STATE"
ENV_SCREENSHOTS_DIR = "LETTER_SCREENSHOTS_DIR"
DEFAULT_SCREENSHOTS_DIR = Path(__file__).parent / "screenshots" / "letter"
DIALOG = '[role="dialog"]'
LETTER_WAIT_MS = 15_000
SHORT_WAIT_MS = 5_000
SETTLE_MS = 400
SHELF_PILL_PATTERN = re.compile(r"Dispatch #\d+")
SCRIBE_HINT = "Make it firmer about the river fords."


async def open_letter_or_exit(page: Page) -> None:
    try:
        await page.wait_for_selector(DIALOG, timeout=LETTER_WAIT_MS)
    except Exception:
        print(
            "No letter dialog opened. This playthrough has no letter armed; "
            "arm one (authored grudge or an earlier negotiation) and rerun."
        )
        sys.exit(2)


async def set_aside_and_reopen(page: Page, shots: Path) -> None:
    print("[2/5] Setting the letter aside and reopening it from the shelf pill...")
    await page.get_by_role("button", name=re.compile("Set it aside", re.I)).click()
    pill = page.get_by_role("button", name=SHELF_PILL_PATTERN)
    await expect(pill).to_be_visible()
    await page.screenshot(path=shots / "shelf-pill.png")
    await pill.click()
    await expect(page.locator(DIALOG)).to_be_visible()


async def draft_with_scribe(page: Page, shots: Path) -> None:
    print("[3/5] Asking the scribe for a draft...")
    await page.get_by_role("button", name=re.compile("Ask my scribe", re.I)).click()
    await expect(
        page.get_by_role("button", name=re.compile("Seal and send", re.I))
    ).to_be_visible()
    await expect(page.get_by_text(re.compile(r"Draft Rev\. 1"))).to_be_visible()
    await page.screenshot(path=shots / "drafting.png")

    print("[4/5] Rewriting with a hint, then undo and redo...")
    await page.get_by_label("Draft hint for scribe").fill(SCRIBE_HINT)
    await page.get_by_role("button", name=re.compile("Rewrite", re.I)).click()
    await expect(page.get_by_text(re.compile(r"Draft Rev\. 2"))).to_be_visible(
        timeout=LETTER_WAIT_MS
    )
    await page.get_by_label("Undo draft change").click()
    await expect(page.get_by_text(re.compile(r"Draft Rev\. 1"))).to_be_visible()
    await page.get_by_label("Redo draft change").click()
    await expect(page.get_by_text(re.compile(r"Draft Rev\. 2"))).to_be_visible()


async def seal_and_confirm_closed(page: Page) -> None:
    print("[5/5] Sealing and sending...")
    await page.get_by_role("button", name=re.compile("Seal and send", re.I)).click()
    await expect(page.locator(DIALOG)).to_have_count(0, timeout=LETTER_WAIT_MS)


async def run_letter_flow() -> None:
    url = os.environ.get(ENV_URL)
    if not url:
        print(f"Set {ENV_URL} to a playthrough URL with an armed letter.")
        sys.exit(2)
    shots = Path(os.environ.get(ENV_SCREENSHOTS_DIR, DEFAULT_SCREENSHOTS_DIR))
    shots.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            storage_state=os.environ.get(ENV_STORAGE_STATE),
        )
        page = await context.new_page()
        print(f"[1/5] Opening {url} and waiting for the letter...")
        await page.goto(url, wait_until="networkidle")
        await open_letter_or_exit(page)
        await page.screenshot(path=shots / "pouch.png")
        await set_aside_and_reopen(page, shots)
        await draft_with_scribe(page, shots)
        await seal_and_confirm_closed(page)
        await browser.close()
    print("Letter flow passed.")


if __name__ == "__main__":
    asyncio.run(run_letter_flow())
