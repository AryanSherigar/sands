"""Where the painted Aldermark map lives and how it reaches storage."""

from pathlib import Path

from app.integrations import storage_client

ASSETS_DIRECTORY = Path(__file__).resolve().parent / "assets"
MAP_ASSET_PATH = ASSETS_DIRECTORY / "map.webp"
MAP_OBJECT_KEY = "aldermark/map.webp"
MAP_CONTENT_TYPE = "image/webp"


def has_map_image() -> bool:
    return MAP_ASSET_PATH.is_file()


def map_image_url() -> str:
    return storage_client.public_url_for(MAP_OBJECT_KEY)


async def upload_map_image() -> str:
    return await storage_client.upload_image(
        MAP_ASSET_PATH.read_bytes(), MAP_CONTENT_TYPE, MAP_OBJECT_KEY
    )
