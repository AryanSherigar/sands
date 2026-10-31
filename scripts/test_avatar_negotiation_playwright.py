import asyncio
import os
import sys
from playwright.async_api import async_playwright, expect

SCREENSHOTS_DIR = "/home/aryan-sherigar/.gemini/antigravity-cli/brain/885d9b40-6210-4f8c-ad27-3d14860afa33/screenshots"
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)


async def test_avatar_negotiation():
    print("=== STARTING PLAYWRIGHT E2E TEST FOR RIVAL MESH AVATAR NEGOTIATION ===")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--enable-webgl", "--use-gl=swiftshader", "--no-sandbox"]
        )
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=1,
        )
        page = await context.new_page()

        # Step 1: Navigate to strategy preview
        print("[1/5] Navigating to http://127.0.0.1:5173/play/strategy-preview...")
        await page.goto("http://127.0.0.1:5173/play/strategy-preview", wait_until="networkidle")
        await page.wait_for_timeout(1000)

        # Step 2: Trigger Negotiation Stage Dialog
        print("[2/5] Triggering Negotiation Stage modal via window.__TRIGGER_NEGOTIATION__()...")
        await page.wait_for_function("typeof window.__TRIGGER_NEGOTIATION__ === 'function'", timeout=10000)
        await page.evaluate("window.__TRIGGER_NEGOTIATION__()")
        await page.wait_for_selector('[role="dialog"]', timeout=5000)

        # Step 3: Verify Negotiation Dossier Layout & Avatar Frame
        print("[3/5] Verifying Negotiation Dossier, Sovereign Header, and Avatar Frame...")
        await expect(page.locator("text=Peace Talks with Queen Mira")).to_be_visible()
        await expect(page.locator("text=Queen Mira").first).to_be_visible()
        await expect(page.locator("text=Sovereign of Dunmere").first).to_be_visible()

        # Locate avatar frame in dossier
        avatar_frame = page.locator(".relative.w-64.h-\\[350px\\]")
        await expect(avatar_frame).to_be_visible()

        shot1_path = os.path.join(SCREENSHOTS_DIR, "avatar-negotiation-initial.png")
        await page.screenshot(path=shot1_path)
        print(f" -> Initial negotiation stage screenshot saved to {shot1_path}")

        # Step 4: Submit Player Speech in 'Say' Mode
        print("[4/5] Submitting player speech to test speech reaction and transcript update...")
        speech_input = page.locator('input[placeholder*="Speak to the ruler"]')
        await speech_input.fill("Dunmere will prosper if our swords remain sheathed.")
        speak_btn = page.locator('button[aria-label="Speak"]')
        await speak_btn.click()
        await page.wait_for_timeout(800)

        # Verify speech rendered in reading chamber
        await expect(page.locator("text=Dunmere will prosper if our swords remain sheathed.")).to_be_visible()
        print(" -> Player speech rendered in reading chamber.")

        shot2_path = os.path.join(SCREENSHOTS_DIR, "avatar-negotiation-after-speech.png")
        await page.screenshot(path=shot2_path)
        print(f" -> Post-speech screenshot saved to {shot2_path}")

        print("[5/5] ALL PLAYWRIGHT E2E ASSERTIONS PASSED SUCCESSFULLY!")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(test_avatar_negotiation())
