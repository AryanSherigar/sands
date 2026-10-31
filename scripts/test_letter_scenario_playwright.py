import asyncio
import os
import sys
from playwright.async_api import async_playwright, expect

SCREENSHOTS_DIR = "/home/aryan-sherigar/.gemini/antigravity-cli/brain/596606ec-752e-4c41-91ed-412ac21585e0"

async def test_letter_scenario():
    print("=== STARTING PLAYWRIGHT E2E TEST FOR STRATEGY LETTER SCENARIO ===")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=1,
        )
        page = await context.new_page()

        # Step 1: Navigate to strategy preview
        print("[1/8] Navigating to http://localhost:5173/play/strategy-preview...")
        await page.goto("http://localhost:5173/play/strategy-preview", wait_until="networkidle")
        await page.wait_for_timeout(1000)

        # Step 2: Trigger Letter Scenario Dialog
        print("[2/8] Triggering Letter Scenario modal...")
        await page.wait_for_function("typeof window.__TRIGGER_LETTER__ === 'function'", timeout=10000)
        await page.evaluate("window.__TRIGGER_LETTER__()")
        await page.wait_for_selector('[role="dialog"]', timeout=5000)

        # Step 3: Verify Stage 1 - Unfolded Courier Pouch
        print("[3/8] Verifying Stage 1 (Courier Pouch)...")
        await expect(page.locator("text=Unfolded Courier Pouch")).to_be_visible()
        await expect(page.locator("text=Queen Mira").first).to_be_visible()
        await expect(page.locator("text=Courteous • Guarded Kin")).to_be_visible()
        await expect(page.locator("text=To my brother Aldric, ruler of the Marches")).to_be_visible()
        await expect(page.locator("text=Mira, Regina")).to_be_visible()
        await expect(page.locator("text=Ask my scribe")).to_be_visible()

        stage1_path = os.path.join(SCREENSHOTS_DIR, "playwright-stage1-pouch.png")
        await page.screenshot(path=stage1_path)
        print(f" -> Stage 1 screenshot saved to {stage1_path}")

        # Step 4: Click 'Ask my scribe' to enter Stage 2 (Drafting Desk)
        print("[4/8] Transitioning to Stage 2 (Drafting Desk)...")
        scribe_btn = page.locator('button:has-text("Ask my scribe")')
        await scribe_btn.click()
        await page.wait_for_timeout(600)

        # Step 5: Verify Stage 2 - Sovereign Desk & Scribe Drafting
        print("[5/8] Verifying Stage 2 layout, spacing, icons and typography...")
        await expect(page.locator("text=Drafting Courier Missive")).to_be_visible()
        await expect(page.get_by_text("Brother Lucan", exact=True)).to_be_visible()
        await expect(page.locator("text=Draft Rev. 1")).to_be_visible()
        await expect(page.locator("text=Marches Council • Privy Scroll")).to_be_visible()
        await expect(page.locator("text=Active Quill: Line 8")).to_be_visible()
        await expect(page.locator("text=Aldric").first).to_be_visible()
        await expect(page.locator("text=Seal and send")).to_be_visible()

        stage2_path = os.path.join(SCREENSHOTS_DIR, "playwright-stage2-scribe-drafting.png")
        await page.screenshot(path=stage2_path)
        print(f" -> Stage 2 screenshot saved to {stage2_path}")

        # Step 6: Test Interactive Scribe Rewrite
        print("[6/8] Testing Scribe Whisper & Rewrite Flow...")
        hint_input = page.locator('input[aria-label="Draft hint for scribe"]')
        await hint_input.fill("Make it firmer on the boundary stones")
        rewrite_btn = page.locator('button:has-text("Rewrite")')
        await rewrite_btn.click()
        await page.wait_for_timeout(400)

        # Verify revision incremented to Rev. 2
        await expect(page.locator("text=Draft Rev. 2")).to_be_visible()
        print(" -> Scribe generated Draft Rev. 2 successfully.")

        # Test Undo
        undo_btn = page.locator('button[aria-label="Undo draft change"]')
        await undo_btn.click()
        await page.wait_for_timeout(300)
        await expect(page.locator("text=Draft Rev. 1")).to_be_visible()
        print(" -> Undo reverted to Draft Rev. 1 successfully.")

        # Test Redo
        redo_btn = page.locator('button[aria-label="Redo draft change"]')
        await redo_btn.click()
        await page.wait_for_timeout(300)
        await expect(page.locator("text=Draft Rev. 2")).to_be_visible()
        print(" -> Redo advanced back to Draft Rev. 2 successfully.")

        # Step 7: Test Sealing and Sending Missive
        print("[7/8] Testing 'Seal and send' submission...")
        seal_btn = page.locator('button:has-text("Seal and send")')
        await seal_btn.click()
        await page.wait_for_timeout(500)
        # Verify dialog closed
        dialog_count = await page.locator('[role="dialog"]').count()
        assert dialog_count == 0, "Dialog should be closed after sealing"
        print(" -> Letter sealed and dialog closed cleanly.")

        # Step 8: Test 'Set it aside' and HUD shelf pill
        print("[8/8] Testing 'Set it aside' shelf pill persistence...")
        await page.evaluate("window.__TRIGGER_LETTER__()")
        await page.wait_for_selector('[role="dialog"]', timeout=5000)
        aside_btn = page.locator('button:has-text("Set it aside")')
        await aside_btn.click()
        await page.wait_for_timeout(500)

        shelf_pill = page.locator('button:has-text("Dispatch #8")')
        await expect(shelf_pill).to_be_visible()
        print(" -> Shelf pill is visible in the top HUD shelf.")

        shelf_path = os.path.join(SCREENSHOTS_DIR, "playwright-stage3-shelf-pill.png")
        await page.screenshot(path=shelf_path)
        print(f" -> Shelf pill screenshot saved to {shelf_path}")

        # Reopen from shelf pill
        await shelf_pill.click()
        await page.wait_for_timeout(400)
        await expect(page.locator("text=Unfolded Courier Pouch")).to_be_visible()
        print(" -> Restored letter scenario dialog from HUD shelf pill.")

        await browser.close()
        print("=== ALL PLAYWRIGHT E2E ASSERTIONS PASSED WITH 100% SUCCESS ===")

if __name__ == "__main__":
    asyncio.run(test_letter_scenario())
