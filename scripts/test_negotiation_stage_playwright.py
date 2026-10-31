import asyncio
import os
import sys
from playwright.async_api import async_playwright, expect

SCREENSHOTS_DIR = "/home/aryan-sherigar/.gemini/antigravity-cli/brain/7f697b12-6447-44b3-a734-4090c008a471/screenshots"
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

async def test_negotiation_stage():
    print("=== STARTING PLAYWRIGHT E2E TEST FOR STRATEGY NEGOTIATION STAGE ===")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=1,
        )
        page = await context.new_page()

        # Step 1: Navigate to strategy preview
        print("[1/8] Navigating to http://127.0.0.1:5173/play/strategy-preview...")
        await page.goto("http://127.0.0.1:5173/play/strategy-preview", wait_until="networkidle")
        await page.wait_for_timeout(1000)

        # Step 2: Trigger Negotiation Stage Dialog
        print("[2/8] Triggering Negotiation Stage modal via window.__TRIGGER_NEGOTIATION__()...")
        await page.wait_for_function("typeof window.__TRIGGER_NEGOTIATION__ === 'function'", timeout=10000)
        await page.evaluate("window.__TRIGGER_NEGOTIATION__()")
        await page.wait_for_selector('[role="dialog"]', timeout=5000)

        # Step 3: Verify Stage Layout (HUD Canopy, Left Dossier, Reading Chamber, Console)
        print("[3/8] Verifying stage layout, headers, dossier, and transcript...")
        await expect(page.locator("text=Exit to Encampment")).to_be_visible()
        await expect(page.locator("text=Peace Talks with Queen Mira")).to_be_visible()
        await expect(page.locator("text=Queen Mira").first).to_be_visible()
        await expect(page.locator("text=Sovereign of Dunmere").first).to_be_visible()
        await expect(page.locator("text=King Alden IV").first).to_be_visible()
        await expect(page.locator("text=340 Gold").first).to_be_visible()
        await expect(page.locator("text=14,200 Levies").first).to_be_visible()
        await expect(page.locator("text=The borderlands of the Valdren Reach stand tense").first).to_be_visible()

        stage1_path = os.path.join(SCREENSHOTS_DIR, "negotiation-stage-initial.png")
        await page.screenshot(path=stage1_path)
        print(f" -> Initial stage screenshot saved to {stage1_path}")

        # Step 4: Submit Player Speech in 'Say' Mode
        print("[4/8] Submitting dialogue in 'Say' mode...")
        speech_input = page.locator('input[placeholder*="Speak to the ruler"]')
        await speech_input.fill("I propose an honorable non-aggression pact between our realms.")
        speak_btn = page.locator('button[aria-label="Speak"]')
        await speak_btn.click()
        await page.wait_for_timeout(500)

        # Verify speech rendered in reading chamber
        await expect(page.locator("text=I propose an honorable non-aggression pact between our realms.")).to_be_visible()
        print(" -> Player speech rendered in reading chamber.")

        # Step 5: Test 'Offer' Mode / Drawer Toggle
        print("[5/8] Toggling 'On the Table' treaty drawer...")
        offer_btn = page.get_by_role("button", name="Offer", exact=True)
        await offer_btn.click()
        await page.wait_for_timeout(400)

        drawer = page.locator('[role="complementary"]').last
        await expect(drawer).to_be_visible()
        await expect(page.locator("text=On the Table")).to_be_visible()
        await expect(page.locator("text=Non-Aggression Pact").first).to_be_visible()

        drawer_path = os.path.join(SCREENSHOTS_DIR, "negotiation-treaty-drawer.png")
        await page.screenshot(path=drawer_path)
        print(f" -> Treaty drawer screenshot saved to {drawer_path}")

        # Step 6: Sign the Pact
        print("[6/8] Signing the treaty pact...")
        sign_btn = page.get_by_role("button", name="Sign the Pact")
        await sign_btn.click()
        await page.wait_for_timeout(600)

        # Step 7: Verify Ratification Overlay with Royal Wax Seal
        print("[7/8] Verifying Ratification Overlay...")
        await expect(page.locator("text=Treaty Sealed & Ratified")).to_be_visible()
        await expect(page.locator("text=The sovereign pact with Queen Mira is sealed under royal wax")).to_be_visible()
        await expect(page.locator("button:has-text('Return to Campaign Map')")).to_be_visible()

        overlay_path = os.path.join(SCREENSHOTS_DIR, "negotiation-ratification-overlay.png")
        await page.screenshot(path=overlay_path)
        print(f" -> Ratification overlay screenshot saved to {overlay_path}")

        # Step 8: Return to Campaign Map
        print("[8/8] Returning to campaign map...")
        return_btn = page.locator('button:has-text("Return to Campaign Map")')
        await return_btn.click()
        await page.wait_for_timeout(500)

        # Verify dialog is dismissed
        dialog_count = await page.locator('[role="dialog"]').count()
        assert dialog_count == 0, f"Expected dialog to be closed, but found {dialog_count}"
        print(" -> Negotiation stage closed cleanly. Returned to map.")

        final_path = os.path.join(SCREENSHOTS_DIR, "negotiation-map-returned.png")
        await page.screenshot(path=final_path)
        print(f" -> Campaign map screenshot saved to {final_path}")

        await context.close()
        await browser.close()
        print("=== PLAYWRIGHT E2E TEST PASSED FLOCKLESSLY! ===")

if __name__ == "__main__":
    asyncio.run(test_negotiation_stage())
