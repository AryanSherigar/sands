import asyncio
import json
import os
import sys
from playwright.async_api import async_playwright, expect

ARTIFACT_DIR = "/home/aryan-sherigar/.gemini/antigravity-cli/brain/a0cd3392-d87f-42c7-b6d4-77852f09737f"
SCREENSHOTS_DIR = os.path.join(ARTIFACT_DIR, "studio-creator-flow")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

REGIONS = [
    {
        "id": "reg_ashford",
        "name": "Ashford",
        "terrain": "farmland",
        "outline": "M 0 0 L 100 0 L 100 100 L 0 100 Z",
        "label_point": {"x": 50, "y": 50},
        "neighbor_ids": ["reg_dunmere"],
        "source_color": None,
        "source_ref": None,
    },
    {
        "id": "reg_dunmere",
        "name": "Dunmere",
        "terrain": "forest",
        "outline": "M 100 0 L 200 0 L 200 100 L 100 100 Z",
        "label_point": {"x": 150, "y": 50},
        "neighbor_ids": ["reg_ashford", "reg_carrow"],
        "source_color": None,
        "source_ref": None,
    },
    {
        "id": "reg_carrow",
        "name": "Carrow",
        "terrain": "hills",
        "outline": "M 200 0 L 300 0 L 300 100 L 200 100 Z",
        "label_point": {"x": 250, "y": 50},
        "neighbor_ids": ["reg_dunmere"],
        "source_color": None,
        "source_ref": None,
    },
]

async def test_studio_creator_flow():
    print("=== STARTING PLAYWRIGHT BROWSER TEST FOR STUDIO CREATOR FLOW ===")
    
    current_scenario = {
        "scenario_id": "scenario-creator-e2e",
        "title": "The Whispering Marches",
        "mode": "strategy",
        "status": "draft",
        "content_tag": "fantasy",
        "content_edited_at": "2026-10-31T20:00:00Z",
        "strategy_document": {
            "title": "The Whispering Marches",
            "end_year": 1004,
            "factions": [
                {
                    "id": "fac_ashford",
                    "name": "House of Ashford",
                    "is_playable": True,
                    "color": "#3b82f6",
                    "capital_region_id": "reg_ashford",
                },
                {
                    "id": "fac_covenant",
                    "name": "Ironmark Covenant",
                    "is_playable": False,
                    "color": "#ef4444",
                    "capital_region_id": "reg_dunmere",
                },
            ],
            "leaders": [
                {
                    "id": "fac_ashford_ruler",
                    "faction_id": "fac_ashford",
                    "name": "Lord Corin",
                    "backstory": "A resolute defender of the eastern reaches.",
                    "trait_ids": ["brave", "cautious"],
                    "ambition_ids": ["fac_ashford_expand"],
                },
                {
                    "id": "fac_covenant_ruler",
                    "faction_id": "fac_covenant",
                    "name": "Warlord Garyth",
                    "backstory": "Hardened commander of the iron legions.",
                    "trait_ids": ["wrathful", "proud"],
                    "ambition_ids": ["fac_covenant_expand"],
                },
            ],
            "ambitions": [
                {
                    "id": "fac_ashford_expand",
                    "name": "Expand Ashford",
                    "condition": {"kind": "controls_region_count", "subject_id": "fac_ashford", "target_count": 3},
                },
                {
                    "id": "fac_covenant_expand",
                    "name": "Covenant Hegemony",
                    "condition": {"kind": "controls_region_count", "subject_id": "fac_covenant", "target_count": 3},
                },
            ],
            "starting": {
                "player_faction_id": "fac_ashford",
                "capitals": {
                    "fac_ashford": "reg_ashford",
                    "fac_covenant": "reg_dunmere",
                },
                "region_ownership": {
                    "reg_ashford": "fac_ashford",
                    "reg_dunmere": "fac_covenant",
                    "reg_carrow": "fac_covenant",
                },
                "region_wealth": {
                    "reg_ashford": 100,
                    "reg_dunmere": 80,
                    "reg_carrow": 60,
                },
                "armies": [
                    {
                        "army_id": "army_ashford_1",
                        "faction_id": "fac_ashford",
                        "region_id": "reg_ashford",
                        "troops": 1000,
                        "commander": {
                            "name": "Sir Eldon",
                            "trait_ids": ["disciplined"],
                            "is_important": True,
                        },
                    },
                    {
                        "army_id": "army_covenant_1",
                        "faction_id": "fac_covenant",
                        "region_id": "reg_dunmere",
                        "troops": 900,
                        "commander": {
                            "name": "Varek the Bold",
                            "trait_ids": ["fierce"],
                            "is_important": True,
                        },
                    },
                ],
            },
        },
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        context = await browser.new_context(
            viewport={"width": 1440, "height": 1024},
            device_scale_factor=1,
        )
        page = await context.new_page()

        # Mock API routes
        async def handle_routes(route):
            url = route.request.url
            method = route.request.method

            if "/v1/auth/refresh" in url:
                return await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps({
                        "access_token": "mock-creator-token",
                        "user": {
                            "user_id": "creator-e2e-user",
                            "display_name": "Studio Creator",
                            "onboarding_completed": True,
                        },
                    }),
                )
            if "/strategy-map" in url:
                return await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps({"regions": REGIONS}),
                )
            if "/strategy-check" in url:
                # Return 0 blocking issues when valid
                return await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps({
                        "blocking": [],
                        "warnings": [
                            {"code": "few_regions", "path": "regions", "message": "The scenario has only 3 regions."}
                        ],
                    }),
                )
            if "/publish" in url:
                current_scenario["status"] = "published"
                return await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps({
                        "scenario_id": current_scenario["scenario_id"],
                        "status": "published",
                        "content_tag": "fantasy",
                    }),
                )
            if "/v1/scenarios/scenario-creator-e2e" in url:
                if method == "PATCH":
                    post_data = route.request.post_data
                    if post_data:
                        patch_data = json.loads(post_data)
                        if "title" in patch_data:
                            current_scenario["title"] = patch_data["title"]
                        if "strategy_document" in patch_data:
                            current_scenario["strategy_document"].update(patch_data["strategy_document"])
                    return await route.fulfill(
                        status=200,
                        content_type="application/json",
                        body=json.dumps(current_scenario),
                    )
                return await route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps(current_scenario),
                )
            
            await route.continue_()

        await page.route("**/v1/**", handle_routes)

        # Step 1: Open Studio Workspace Page
        print("[1/6] Navigating to Studio workspace page...")
        await page.goto("http://127.0.0.1:5173/studio/scenario-creator-e2e/edit", wait_until="networkidle")
        await page.wait_for_timeout(1000)

        # Step 2: Verify page structure & headers
        print("[2/6] Verifying Strategy Studio headers & workspace layout...")
        await expect(page.locator("h1:has-text('Strategy scenario')")).to_be_visible(timeout=10000)
        await expect(page.locator("text=All changes saved")).to_be_visible()
        
        # Verify Sections exist
        await expect(page.get_by_role("heading", name="1. Map")).to_be_visible()
        await expect(page.get_by_role("heading", name="2. Factions and leaders")).to_be_visible()
        await expect(page.get_by_role("heading", name="3. Starting regions")).to_be_visible()
        await expect(page.get_by_role("heading", name="4. Starting situation")).to_be_visible()
        await expect(page.get_by_role("heading", name="5. Publish")).to_be_visible()

        shot1 = os.path.join(SCREENSHOTS_DIR, "01-studio-workspace-overview.png")
        await page.screenshot(path=shot1, full_page=True)
        print(f" -> Screenshot 1 saved: {shot1}")

        # Step 3: Verify Factions & Leader details
        print("[3/6] Verifying Faction Cards & Leaders...")
        faction_inputs = page.locator('input[aria-label="Faction name"]')
        await expect(faction_inputs.first).to_have_value("House of Ashford")
        await expect(faction_inputs.nth(1)).to_have_value("Ironmark Covenant")

        leader_inputs = page.locator('label:has-text("Leader name") input')
        await expect(leader_inputs.first).to_have_value("Lord Corin")
        await expect(leader_inputs.nth(1)).to_have_value("Warlord Garyth")

        shot2 = os.path.join(SCREENSHOTS_DIR, "02-studio-factions-verified.png")
        await page.screenshot(path=shot2)
        print(f" -> Screenshot 2 saved: {shot2}")

        # Step 4: Verify Starting Armies & Region Setup in Start Section
        print("[4/6] Verifying Starting situation setup (armies, regions)...")
        # Scroll down to Starting Situation
        start_section = page.get_by_role("heading", name="3. Starting regions")
        await start_section.scroll_into_view_if_needed()
        await page.wait_for_timeout(500)

        shot3 = os.path.join(SCREENSHOTS_DIR, "03-studio-starting-situation.png")
        await page.screenshot(path=shot3)
        print(f" -> Screenshot 3 saved: {shot3}")

        # Step 5: Verify Publish Section & Readiness Check
        print("[5/6] Verifying 5. Publish section and publish readiness...")
        publish_section = page.get_by_role("heading", name="5. Publish")
        await publish_section.scroll_into_view_if_needed()
        await page.wait_for_timeout(500)

        # Check that warning is rendered (few_regions)
        await expect(page.locator("text=The scenario has only 3 regions.")).to_be_visible()
        print(" -> Publish readiness check rendered clean warning (0 blocking issues).")

        # Publish button must be enabled
        publish_btn = page.locator('button:has-text("Publish")')
        await expect(publish_btn).to_be_enabled()
        print(" -> Publish button is enabled!")

        shot4 = os.path.join(SCREENSHOTS_DIR, "04-studio-publish-readiness.png")
        await page.screenshot(path=shot4)
        print(f" -> Screenshot 4 saved: {shot4}")

        # Step 6: Trigger Publish and verify Published state
        print("[6/6] Clicking Publish button...")
        await publish_btn.click()
        await page.wait_for_timeout(1000)

        # Verify Published status text appears
        await expect(page.locator("text=Published.")).to_be_visible(timeout=5000)
        print(" -> Scenario published successfully in browser!")

        shot5 = os.path.join(SCREENSHOTS_DIR, "05-studio-published-success.png")
        await page.screenshot(path=shot5)
        print(f" -> Screenshot 5 saved: {shot5}")

        await browser.close()
        print("=== BROWSER CREATOR FLOW COMPLETED AND VERIFIED CLEAN ===")

if __name__ == "__main__":
    asyncio.run(test_studio_creator_flow())
