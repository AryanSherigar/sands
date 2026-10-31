import sys
from playwright.sync_api import sync_playwright

def test_fog_of_war_e2e():
    print("[E2E] Starting Playwright Fog of War End-to-End Suite...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        print("[E2E] Navigating to http://localhost:5173/play/strategy-preview...")
        page.goto("http://localhost:5173/play/strategy-preview", wait_until="networkidle", timeout=30000)

        # 1. Check SVG region outline path classes in Political mode
        print("[E2E] Checking province SVG outlines in Political map mode...")
        dunmere = page.locator('svg path[data-region-id="reg-dunmere"]')
        highcrag = page.locator('svg path[data-region-id="reg-highcrag"]')
        silverwood = page.locator('svg path[data-region-id="reg-silverwood"]')

        dunmere_class = dunmere.get_attribute("class") or ""
        highcrag_class = highcrag.get_attribute("class") or ""
        silverwood_class = silverwood.get_attribute("class") or ""

        # Visible provinces have lantern stroke
        assert "stroke-[#FFF8E7]/90" in dunmere_class, f"Dunmere missing lantern stroke: {dunmere_class}"
        assert "stroke-[#FFF8E7]/90" in silverwood_class, f"Silverwood missing lantern stroke: {silverwood_class}"

        # Fogged province has shadow fill and muted ink stroke
        assert "fill-[#3A3128]/25" in highcrag_class, f"High Crag missing shadow fill: {highcrag_class}"
        assert "stroke-[#3A3128]/40" in highcrag_class, f"High Crag missing muted stroke: {highcrag_class}"
        print("  ✓ Dunmere & Silverwood have illuminated lantern stroke")
        print("  ✓ High Crag has vellum shadow fill and muted ink stroke")

        # 2. Hostile army in fogged region must NOT be rendered
        print("[E2E] Checking army visibility...")
        friendly_army = page.locator("text=1st Royal Host").or_(page.locator("text=1ST ROYAL HOST"))
        assert friendly_army.count() > 0, "Friendly army 1st Royal Host should be rendered"
        print("  ✓ Friendly army (1st Royal Host) in visible territory is rendered")

        hostile_army = page.locator("text=Ironmark Host").or_(page.locator("text=IRONMARK HOST"))
        assert hostile_army.count() == 0, "Hostile army in fogged High Crag must be strictly concealed"
        print("  ✓ Hostile army in fogged High Crag is strictly concealed")

        # 3. Switch to Fog map mode
        print("[E2E] Testing 'Fog' map mode switch...")
        fog_btn = page.locator('button:has-text("Fog")').or_(page.locator('button:has-text("fog")'))
        fog_btn.first.click()
        page.wait_for_timeout(500)

        dunmere_fog_class = dunmere.get_attribute("class") or ""
        highcrag_fog_class = highcrag.get_attribute("class") or ""

        assert "fill-[#E8B86D]/35" in dunmere_fog_class, f"Dunmere missing amber illumination: {dunmere_fog_class}"
        assert "fill-[#2D2319]/40" in highcrag_fog_class, f"High Crag missing umber shadow: {highcrag_fog_class}"
        print("  ✓ Fog mode amber illumination active on Dunmere")
        print("  ✓ Fog mode umber shadow active on High Crag")

        # 4. Click fogged province pin to inspect charter
        print("[E2E] Clicking High Crag Keep to verify Provincial Charter masking...")
        highcrag_pin = page.locator('button:has-text("High Crag Keep")').or_(page.locator('text=High Crag Keep'))
        highcrag_pin.first.click()
        page.wait_for_timeout(500)

        charter = page.locator("text=PROVINCIAL CHARTER")
        assert charter.count() > 0, "Provincial Charter inspector should be open"

        # Verify physical geography is visible
        assert page.locator("text=Mountain").count() > 0, "Physical Mountain terrain must be visible"
        assert page.locator("text=Ironmark March").count() > 0, "Known owner Ironmark March must be visible"

        # Verify dynamic stats are masked as Unobserved
        unobserved_labels = page.locator("text=Unobserved")
        assert unobserved_labels.count() >= 4, f"Expected at least 4 'Unobserved' metrics, found {unobserved_labels.count()}"
        print(f"  ✓ Found {unobserved_labels.count()} dynamic metrics masked as 'Unobserved'")

        # 5. Click friendly/observed province to verify stats are NOT masked
        print("[E2E] Clicking Dunmere Vale to verify unmasked observed metrics...")
        dunmere_pin = page.locator('button:has-text("Dunmere Vale")').or_(page.locator('text=Dunmere Vale'))
        dunmere_pin.first.click()
        page.wait_for_timeout(500)

        # Dunmere is player-owned and visible, should show real numbers
        assert page.locator("text=42,800").count() > 0, "Dunmere population 42,800 should be visible"
        print("  ✓ Observed Dunmere displays real dynamic metrics (42,800)")

        browser.close()
        print("\n[E2E] ALL PLAYWRIGHT & DEVTOOLS TESTS PASSED SUCCESSFULLY! ✨")

if __name__ == "__main__":
    try:
        test_fog_of_war_e2e()
    except Exception as e:
        print(f"[E2E ERROR] {e}", file=sys.stderr)
        sys.exit(1)
