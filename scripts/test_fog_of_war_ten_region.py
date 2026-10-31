import sys
from playwright.sync_api import sync_playwright

def test_fog_of_war_ten_region():
    print("[E2E-10] Starting Playwright 10-Region Fog of War Suite...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        url = "http://localhost:5173/play/strategy-preview?demo=10-region"
        print(f"[E2E-10] Navigating to {url}...")
        page.goto(url, wait_until="networkidle", timeout=30000)

        # 1. Verify all 10 regions exist
        print("[E2E-10] Verifying all 10 regions exist on canvas...")
        expected_regions = [
            "aldgate", "ashford", "brennmoor", "dunwick", "gull_point",
            "carrow_vale", "kings_ford", "fenwatch", "elmstead", "high_meadow"
        ]
        for reg_id in expected_regions:
            locator = page.locator(f'svg path[data-region-id="{reg_id}"]')
            assert locator.count() == 1, f"Missing region on canvas: {reg_id}"
        print(f"  ✓ All {len(expected_regions)} regions verified on strategy map canvas")

        # 2. Check Political mode Fog of War styling
        print("[E2E-10] Checking Political mode illumination and shadow...")
        visible_regs = ["carrow_vale", "elmstead", "high_meadow", "ashford", "kings_ford", "fenwatch"]
        fogged_regs = ["aldgate", "brennmoor", "dunwick"]

        for reg_id in visible_regs:
            cls = page.locator(f'svg path[data-region-id="{reg_id}"]').get_attribute("class") or ""
            assert "stroke-[#FFF8E7]/90" in cls, f"Visible region {reg_id} missing lantern stroke: {cls}"

        for reg_id in fogged_regs:
            cls = page.locator(f'svg path[data-region-id="{reg_id}"]').get_attribute("class") or ""
            assert "fill-[#3A3128]/25" in cls, f"Fogged region {reg_id} missing shadow fill: {cls}"
            assert "stroke-[#3A3128]/40" in cls, f"Fogged region {reg_id} missing muted stroke: {cls}"

        print(f"  ✓ All {len(visible_regs)} visible regions display gold lantern stroke highlights")
        print(f"  ✓ All {len(fogged_regs)} fogged regions display cool vellum shadow & muted ink strokes")

        # 3. Troop concealment
        print("[E2E-10] Checking troop concealment across 10 regions...")
        # Friendly armies should be visible
        assert page.locator("text=Brand's Vanguard").or_(page.locator("text=BRAND'S VANGUARD")).count() > 0, "Friendly army Brand's Vanguard should be visible"
        assert page.locator("text=Coast Watch").or_(page.locator("text=COAST WATCH")).count() > 0, "Friendly army Coast Watch should be visible"
        print("  ✓ Friendly armies in Carrow Vale and Elmstead are visible")

        # Hostile army in visible territory should be visible
        assert page.locator("text=Renaud's Legion").or_(page.locator("text=RENAUD'S LEGION")).count() > 0, "Hostile army in visible Ashford should be visible"
        print("  ✓ Hostile army in visible Ashford is visible")

        # Hostile armies in fogged territory should be strictly concealed
        assert page.locator("text=Tormund's Iron Host").or_(page.locator("text=TORMUND'S IRON HOST")).count() == 0, "Hostile army in fogged Dunwick must be concealed"
        assert page.locator("text=Aldgate Garrison").or_(page.locator("text=ALDGATE GARRISON")).count() == 0, "Hostile army in fogged Aldgate must be concealed"
        print("  ✓ Hostile armies in fogged Dunwick and Aldgate are strictly concealed")

        # 4. Switch to Fog map mode
        print("[E2E-10] Switching to 'Fog' map mode...")
        fog_btn = page.locator('button:has-text("Fog")').or_(page.locator('button:has-text("fog")'))
        fog_btn.first.click()
        page.wait_for_timeout(500)

        carrow_cls = page.locator('svg path[data-region-id="carrow_vale"]').get_attribute("class") or ""
        dunwick_cls = page.locator('svg path[data-region-id="dunwick"]').get_attribute("class") or ""

        assert "fill-[#E8B86D]/35" in carrow_cls, f"Carrow Vale missing amber fill in fog mode: {carrow_cls}"
        assert "fill-[#2D2319]/40" in dunwick_cls, f"Dunwick missing umber fill in fog mode: {dunwick_cls}"
        print("  ✓ Fog mode styling confirmed: amber illumination on Carrow Vale, umber shadow on Dunwick")

        # 5. Provincial Charter masking on fogged region Dunwick
        print("[E2E-10] Clicking fogged Dunwick to verify Provincial Charter masking...")
        dunwick_pin = page.locator('button:has-text("Dunwick")').or_(page.locator('text=Dunwick'))
        dunwick_pin.first.click()
        page.wait_for_timeout(500)

        assert page.locator("text=PROVINCIAL CHARTER").count() > 0, "Charter inspector should be open"
        assert page.locator("text=Forest").count() > 0, "Terrain type Forest should be visible"

        unobserved_count = page.locator("text=Unobserved").count()
        assert unobserved_count >= 4, f"Expected >= 4 unobserved metrics, found {unobserved_count}"
        print(f"  ✓ Confirmed {unobserved_count} dynamic metrics masked as 'Unobserved' on fogged Dunwick")

        # 6. Click observed region Carrow Vale to verify real metrics
        print("[E2E-10] Clicking observed Carrow Vale to verify real metrics...")
        carrow_pin = page.locator('button:has-text("Carrow Vale")').or_(page.locator('text=Carrow Vale'))
        carrow_pin.first.click()
        page.wait_for_timeout(500)

        assert page.locator("text=800").count() > 0, "Population 800 should be visible for Carrow Vale"
        print("  ✓ Confirmed real provincial metrics for observed Carrow Vale")

        # 7. Test Demo Scenario toggle button
        print("[E2E-10] Testing Demo Scenario toggle button...")
        toggle_btn = page.locator('aside[aria-label="Demo scenario picker"] button')
        assert toggle_btn.count() > 0, "Demo scenario toggle button should exist"
        toggle_btn.first.click()
        page.wait_for_timeout(500)

        # Should now be 4-region map with Dunmere Vale
        assert page.locator('svg path[data-region-id="reg-dunmere"]').count() > 0, "Should have switched to 4-region map"
        print("  ✓ Successfully toggled to 4-region map")

        toggle_btn.first.click()
        page.wait_for_timeout(500)
        assert page.locator('svg path[data-region-id="carrow_vale"]').count() > 0, "Should have switched back to 10-region map"
        print("  ✓ Successfully toggled back to 10-region map")

        browser.close()
        print("\n[E2E-10] ALL 10-REGION FOG OF WAR PLAYWRIGHT TESTS PASSED! ✨")

if __name__ == "__main__":
    try:
        test_fog_of_war_ten_region()
    except Exception as e:
        print(f"[E2E-10 ERROR] {e}", file=sys.stderr)
        sys.exit(1)
