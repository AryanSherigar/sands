"""Upload the Night Desk cover image to object storage."""

from pathlib import Path

from app.integrations import storage_client

COVER_PATH = Path(__file__).parent / "assets" / "cover.jpg"
COVER_CONTENT_TYPE = "image/jpeg"
COVER_OBJECT_KEY = "night-desk/cover.jpg"


async def upload_cover(cover_path: Path = COVER_PATH) -> str:
    if not cover_path.is_file():
        raise FileNotFoundError(f"Missing cover image at {cover_path}")
    return await storage_client.upload_image(
        cover_path.read_bytes(), COVER_CONTENT_TYPE, COVER_OBJECT_KEY
    )
