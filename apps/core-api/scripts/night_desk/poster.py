"""The TrueFeel poster shown in the lobby: its object key and public URL."""

from pathlib import Path

from app.integrations import storage_client

POSTER_OBJECT_KEY = "night-desk/truefeel-poster.png"
POSTER_CONTENT_TYPE = "image/png"
POSTER_PATH = Path(__file__).parent / "assets" / "truefeel-poster.png"


def poster_url() -> str:
    return storage_client.public_url_for(POSTER_OBJECT_KEY)


async def upload_poster(poster_path: Path = POSTER_PATH) -> str:
    if not poster_path.is_file():
        raise FileNotFoundError(f"Missing poster image at {poster_path}")
    return await storage_client.upload_image(
        poster_path.read_bytes(), POSTER_CONTENT_TYPE, POSTER_OBJECT_KEY
    )
