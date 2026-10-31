from playwright.sync_api import sync_playwright

def capture_screenshots():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        page.goto("http://localhost:5173/play/strategy-preview?demo=10-region", wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(1000)

        # 1. Political mode overview
        page.screenshot(path="/data/sands/docs/screenshots/ten_region_political.png")
        print("Captured ten_region_political.png")

        # 2. Fog map mode
        fog_btn = page.locator('button:has-text("Fog")').or_(page.locator('button:has-text("fog")'))
        fog_btn.first.click()
        page.wait_for_timeout(500)
        page.screenshot(path="/data/sands/docs/screenshots/ten_region_fog_mode.png")
        print("Captured ten_region_fog_mode.png")

        # 3. Click fogged Dunwick inspector
        dunwick_pin = page.locator('button:has-text("Dunwick")').or_(page.locator('text=Dunwick'))
        dunwick_pin.first.click()
        page.wait_for_timeout(500)
        page.screenshot(path="/data/sands/docs/screenshots/ten_region_fogged_inspector.png")
        print("Captured ten_region_fogged_inspector.png")

        # 4. Click observed Carrow Vale inspector
        carrow_pin = page.locator('button:has-text("Carrow Vale")').or_(page.locator('text=Carrow Vale'))
        carrow_pin.first.click()
        page.wait_for_timeout(500)
        page.screenshot(path="/data/sands/docs/screenshots/ten_region_observed_inspector.png")
        print("Captured ten_region_observed_inspector.png")

        browser.close()

if __name__ == "__main__":
    capture_screenshots()
