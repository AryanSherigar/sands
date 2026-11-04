"""Upload the four Night Desk tier tracks to object storage."""

from pathlib import Path

from app.integrations import storage_client
from scripts.night_desk.hints import TENSION_TRACKS

ASSETS_DIR = Path(__file__).parent / "assets"
TRACK_CONTENT_TYPE = "audio/mpeg"


def find_missing_tracks(assets_dir: Path = ASSETS_DIR) -> list[str]:
    return [
        f"{tier}.mp3"
        for tier in TENSION_TRACKS
        if not (assets_dir / f"{tier}.mp3").is_file()
    ]


async def upload_tier_tracks(assets_dir: Path = ASSETS_DIR) -> dict[str, str]:
    missing = find_missing_tracks(assets_dir)
    if missing:
        raise FileNotFoundError(f"Missing tier tracks in {assets_dir}: {missing}")
    urls: dict[str, str] = {}
    for tier, object_key in TENSION_TRACKS.items():
        content = (assets_dir / f"{tier}.mp3").read_bytes()
        urls[tier] = await storage_client.upload_image(
            content, TRACK_CONTENT_TYPE, object_key
        )
        if urls[tier] != storage_client.public_url_for(object_key):
            raise RuntimeError(f"Uploaded URL for '{tier}' does not match its key")
    return urls
