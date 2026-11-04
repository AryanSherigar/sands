"""Render poster.html to ../truefeel-poster.png (run once; the PNG is committed).

Needs Playwright with a Chromium build, which is a development tool and not a
runtime dependency of the Core API:

    python scripts/night_desk/assets/poster/render_poster.py [--chromium PATH]
"""

import argparse
import asyncio
from pathlib import Path

from playwright.async_api import async_playwright

POSTER_DIR = Path(__file__).parent
HTML_PATH = POSTER_DIR / "poster.html"
OUTPUT_PATH = POSTER_DIR.parent / "truefeel-poster.png"
POSTER_SELECTOR = "#poster"
VIEWPORT = {"width": 1080, "height": 1528}
FONT_SETTLE_MS = 800


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chromium", type=Path, default=None)
    return parser.parse_args()


async def render(chromium: Path | None) -> Path:
    async with async_playwright() as playwright:
        launch = {"executable_path": str(chromium)} if chromium else {}
        browser = await playwright.chromium.launch(**launch)
        page = await browser.new_page(viewport=VIEWPORT)
        await page.goto(HTML_PATH.as_uri(), wait_until="networkidle")
        await page.evaluate("document.fonts.ready")
        await page.wait_for_timeout(FONT_SETTLE_MS)
        await page.locator(POSTER_SELECTOR).screenshot(path=str(OUTPUT_PATH))
        await browser.close()
    return OUTPUT_PATH


def main() -> None:
    print(f"Rendered {asyncio.run(render(parse_args().chromium))}")


if __name__ == "__main__":
    main()
