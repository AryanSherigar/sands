import asyncio
import os
import shutil
from playwright.async_api import async_playwright, expect
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


SCREENSHOTS_DIR = str(REPO_ROOT / "scripts" / "screenshots" / "war_council")
ARTIFACT_DIR = "/home/aryan-sherigar/.gemini/antigravity-cli/brain/5e66f7ed-207b-4a71-a40c-a8783f2375c0"

async def test_war_council_e2e():
    print("=== STARTING PLAYWRIGHT E2E TEST: WAR COUNCIL REAL WIRING ===")
    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
    os.makedirs(ARTIFACT_DIR, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=1,
        )
        page = await context.new_page()

        # Step 1: Navigate to the War Council preview page
        print("[1/7] Navigating to http://127.0.0.1:5173/play/war-council-preview...")
        await page.goto("http://127.0.0.1:5173/play/war-council-preview", wait_until="networkidle")
        await page.wait_for_timeout(1000)

        shot1 = f"{SCREENSHOTS_DIR}/01_war_council_initial.png"
        await page.screenshot(path=shot1, full_page=True)
        print(f" -> Screenshot saved: {shot1}")

        # Step 2: Verify HUD Elements (Mandates, Frontage, Title, Atmosphere)
        print("[2/7] Verifying HUD Mandates and Frontage Bottleneck...")
        await expect(page.locator("text=/0 Royal Mandates/i").first).to_be_visible()
        await expect(page.locator("text=/Frontage: 2,500/i").first).to_be_visible()
        await expect(page.locator("text=/Battle of/i").first).to_be_visible()
        print(" -> HUD verification passed!")

        # Step 3: Verify Left Rail and Center Reconnaissance Intervals
        print("[3/7] Verifying Medieval Reconnaissance & Commanders...")
        await expect(page.locator("text=Lord Aldric Vane").first).to_be_visible()
        await expect(page.locator("text=Warlord Brand").first).to_be_visible()
        await expect(page.locator("text=/~1,200/i").first).to_be_visible()
        print(" -> Medieval reconnaissance intervals verified!")

        # Step 4: Interact with Player Ward Ranks & Steppers
        print("[4/7] Testing Ward Steppers and Rank Controls...")
        # Verify 3 Wards exist
        await expect(page.locator("text=/Center.*Main Battle/i").first).to_be_visible()
        await expect(page.locator("text=/TACTIC ANCHOR/i").first).to_be_visible()

        # Find plus buttons for cohort steppers and click one
        plus_buttons = page.locator('button:has-text("+")')
        count_before = await plus_buttons.count()
        print(f" -> Found {count_before} stepper buttons across wards")
        if count_before > 0:
            await plus_buttons.first.click()
            await page.wait_for_timeout(300)

        shot2 = f"{SCREENSHOTS_DIR}/02_ward_steppers_adjusted.png"
        await page.screenshot(path=shot2, full_page=True)
        print(f" -> Screenshot saved: {shot2}")

        # Step 5: Test Doctrine Selection & Terrain Prerequisite
        print("[5/7] Testing Historical Doctrines...")
        await expect(page.locator("text=/Boar's Snout/i").first).to_be_visible()
        await expect(page.locator("text=/Shield-Wall Anchor/i").first).to_be_visible()
        await expect(page.locator("text=/Requires Forest terrain/i").first).to_be_visible()

        # Click Boar's Snout Wedge doctrine card
        boar_card = page.locator('button:has-text("Boar\'s Snout")')
        if await boar_card.count() > 0:
            await boar_card.first.click()
            await page.wait_for_timeout(300)
            print(" -> Selected Boar's Snout Wedge doctrine!")

        shot3 = f"{SCREENSHOTS_DIR}/03_doctrine_selected.png"
        await page.screenshot(path=shot3, full_page=True)
        print(f" -> Screenshot saved: {shot3}")

        # Step 6: Commit to Battle (Wave 1)
        print("[6/7] Committing to Battle (Wave 1 Clash)...")
        commit_btn = page.locator('button:has-text("Commit to Battle")').first
        await expect(commit_btn).to_be_visible()
        await commit_btn.click()
        await page.wait_for_timeout(1000)

        shot4 = f"{SCREENSHOTS_DIR}/04_wave_manuscript_modal.png"
        await page.screenshot(path=shot4, full_page=True)
        print(f" -> Screenshot saved: {shot4}")

        # Step 7: Verify Exchange Manuscript Modal (Option A Rank-by-Rank Receipts)
        print("[7/7] Verifying Option A Rank-by-Rank Casualty Receipts...")
        dialog = page.locator('dialog, [role="dialog"]').first
        await expect(dialog).to_be_visible(timeout=5000)
        await expect(dialog.locator("text=/Wave 1 Clash Manuscript/i")).to_be_visible()

        # Verify rank breakdown narratives exist inside the manuscript dialog
        await expect(dialog.locator("text=/shields held firm/i")).to_be_visible()
        await expect(dialog.locator("text=/bodkins perforated/i")).to_be_visible()
        print(" -> Rank-by-Rank casualty receipt confirmed inside manuscript modal!")

        # Advance to Wave 2
        advance_btn = dialog.locator('button:has-text("Advance to Wave 2")')
        await expect(advance_btn).to_be_visible()
        await advance_btn.click()
        await page.wait_for_timeout(600)
        print(" -> Successfully clicked Advance to Wave 2!")

        shot5 = f"{SCREENSHOTS_DIR}/05_wave2_resumed.png"
        await page.screenshot(path=shot5, full_page=True)
        print(f" -> Screenshot saved: {shot5}")

        # Copy screenshots to artifact directory for persistent inspection
        for f in os.listdir(SCREENSHOTS_DIR):
            if f.endswith(".png"):
                shutil.copy(os.path.join(SCREENSHOTS_DIR, f), os.path.join(ARTIFACT_DIR, f))

        await browser.close()
        print("=== PLAYWRIGHT E2E WAR COUNCIL TEST COMPLETED SUCCESSFULLY ===")

if __name__ == "__main__":
    asyncio.run(test_war_council_e2e())
