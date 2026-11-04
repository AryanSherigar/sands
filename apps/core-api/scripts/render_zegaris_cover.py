"""Generate a Zegaris cover candidate with the existing Core API cover path (one Muse image).

Run via:
    python -m scripts.render_zegaris_cover --style {glass,icon,fresco} [--size WxH] [--output PATH]

Each run spends one Muse image unit; the result is copied to the committed
asset path that seed_zegaris uploads.
"""

import argparse
import asyncio
import shutil
import uuid
from pathlib import Path

from app.config import settings
from app.db.models.user import User
from app.models.image_generation import CoverImageGenerationRequest
from app.services.upload_service import UploadService
from scripts.zegaris.map_assets import COVER_ASSET_PATH

EYES = (
    "her eyelids closed and sunken, the sockets smooth and shadowed, no eyes "
    "visible, no blood, the rest of her face fully painted in natural flesh "
    "tones with a calm, protective expression"
)
COVER_STYLES: dict[str, str] = {
    "glass": (
        "A wide view from inside a stone cathedral nave, looking down the aisle "
        "at one tall pointed-arch stained-glass window in the far wall, centred. "
        "The window shows a serene priestess in white robes facing the viewer, "
        f"{EYES}, a field of molten gold glass behind her set in black lead "
        "lines, bright enough to read clearly. The nave is dim but not black: "
        "dressed-stone piers and ribbed vaults on both sides, worn flagstones, "
        "a few rows of empty plain wooden pews. Coloured light from the window "
        "falls in uneven patches across the floor. Painted in oil, restrained "
        "palette of warm gold, ash-grey and umber, soft edges, no sharp "
        "digital rendering. No people, no text, no lettering."
    ),
    "icon": (
        "A wide Byzantine icon painted in egg tempera on a flat gold-leaf "
        "ground, in the manner of the Virgin of Vladimir, with the gilded "
        "ornament of Klimt's The Kiss. A half-length frontal priestess sits "
        "left of centre, her head slightly inclined, a long narrow face with "
        f"soft olive-brown modelling, {EYES}. Her robe and veil are white and "
        "pale straw, patterned with hand-gilded spirals, small circles and "
        "rectangles. The gold ground fills the rest of the wide panel, with "
        "fine craquelure and a few small worn patches. A thin dark border and a "
        "thin red inner line frame it. Flat, hieratic, no perspective, no cast "
        "shadows. No text, no lettering, no inscription."
    ),
    "fresco": (
        "A wide section of a buon fresco on a lime-plaster chapel wall in the "
        "manner of a late medieval Italian painter: a standing priestess in "
        f"white robes, frontal, centred, {EYES}. High behind her shoulder hangs "
        "a dark eclipsed sun with a thin ring of yellow-ochre light, not a halo. "
        "Warm pink-ochre plaster ground. Pigment sunk into the plaster, so the "
        "surface is matte and chalky, in a limited earth palette of yellow "
        "ochre, red earth, lime white and soot black. Visible seams where one "
        "day's plaster meets the next, hairline cracks, small flaked losses "
        "showing bare plaster, outlines drawn loosely in red earth, flat "
        "modelling with simple hatched shadow. No text, no lettering."
    ),
}
STYLE_FILE_NAMES = {key: f"cover-{key}.webp" for key in COVER_STYLES}
COVER_SIZE_REQUEST = "1792x1008"
UPLOADS_URL_MARKER = "/uploads/"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--style", choices=sorted(COVER_STYLES), required=True)
    parser.add_argument("--size", default=COVER_SIZE_REQUEST)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def stored_path_for(cover_url: str) -> Path:
    object_key = cover_url.split(UPLOADS_URL_MARKER, 1)[1]
    return Path(settings.local_upload_dir) / object_key


async def render(style: str, size: str, output: Path) -> None:
    service = UploadService(quota_service=None)
    request = CoverImageGenerationRequest(
        title="Zegaris",
        genre_tags=["high fantasy"],
        opening_scene=COVER_STYLES[style],
    )
    url = await service.generate_and_upload_cover_image(
        request, User(user_id=uuid.uuid4()), size=size
    )
    stored = stored_path_for(url)
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(stored, output)
    stored.unlink()
    print(f"Wrote {output}")


def main() -> None:
    args = parse_args()
    output = args.output or COVER_ASSET_PATH.with_name(STYLE_FILE_NAMES[args.style])
    asyncio.run(render(args.style, args.size, output))


if __name__ == "__main__":
    main()
