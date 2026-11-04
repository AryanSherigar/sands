"""Where the painted Zegaris map and cover live and how they reach storage."""

from pathlib import Path

from app.integrations import storage_client

MAP_ASSET_PATH = Path(__file__).resolve().parent / "assets" / "imperial-highway.webp"
MAP_OBJECT_KEY = "zegaris/maps/imperial-highway.webp"
MAP_CONTENT_TYPE = "image/webp"


def has_map_image() -> bool:
    return MAP_ASSET_PATH.is_file()


def map_image_url() -> str:
    return storage_client.public_url_for(MAP_OBJECT_KEY)


async def upload_map_image() -> str:
    return await storage_client.upload_image(
        MAP_ASSET_PATH.read_bytes(), MAP_CONTENT_TYPE, MAP_OBJECT_KEY
    )


COVER_ASSET_PATH = Path(__file__).resolve().parent / "assets" / "cover.webp"
COVER_OBJECT_KEY = "zegaris/cover.webp"


def has_cover_image() -> bool:
    return COVER_ASSET_PATH.is_file()


def cover_image_url() -> str:
    return storage_client.public_url_for(COVER_OBJECT_KEY)


async def upload_cover_image() -> str:
    return await storage_client.upload_image(
        COVER_ASSET_PATH.read_bytes(), MAP_CONTENT_TYPE, COVER_OBJECT_KEY
    )
