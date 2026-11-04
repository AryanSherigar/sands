"""Paint the Imperial Highway map with strategy's art step (one Muse image edit).

Run via:
    python -m scripts.render_zegaris_map [--output PATH]

Builds the flat-color guide, sends it through MapGenerationService.generate_art
and copies the painted WebP to the committed asset path that seed_zegaris
uploads. Each run spends one Muse image unit.
"""

import argparse
import asyncio
import shutil
import uuid
from pathlib import Path

from app.config import settings
from app.db.models.user import User
from app.services.map_generation_service import MapGenerationService
from scripts.zegaris.map_assets import MAP_ASSET_PATH
from scripts.zegaris.mapart import build_guide_png

MAP_DESCRIPTION = (
    "a high mountain pass between two realms: jagged shale crags and a dark "
    "chasm in the west, a bare pass with a crossroads in the middle, and a "
    "warm green valley in the east with muddy flats outside the walls and "
    "pale terraced hills rising to a white city in the far north-east; one "
    "pale road runs from the western crags through the pass into the valley"
)
UPLOADS_URL_MARKER = "/uploads/"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=MAP_ASSET_PATH)
    return parser.parse_args()


def stored_path_for(picture_url: str) -> Path:
    object_key = picture_url.split(UPLOADS_URL_MARKER, 1)[1]
    return Path(settings.local_upload_dir) / object_key


async def render(output: Path) -> None:
    service = MapGenerationService(quota_service=None)
    art = await service.generate_art(
        build_guide_png(), MAP_DESCRIPTION, User(user_id=uuid.uuid4())
    )
    stored = stored_path_for(art.picture_url)
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(stored, output)
    stored.unlink()
    print(f"Wrote {output} ({art.width}x{art.height})")


def main() -> None:
    asyncio.run(render(parse_args().output))


if __name__ == "__main__":
    main()
