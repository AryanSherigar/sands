"""Object keys, public URLs and the upload of the generated map images."""

from pathlib import Path

from app.integrations import storage_client
from scripts.reincarnated_aristocrat.mapart.constants import MAP_ASSET_DIR

MAP_OBJECT_PREFIX = "reincarnated-aristocrat/maps"
MAP_CONTENT_TYPE = "image/png"


def map_object_key(file_name: str) -> str:
    return f"{MAP_OBJECT_PREFIX}/{file_name}"


def map_image_url(file_name: str) -> str:
    return storage_client.public_url_for(map_object_key(file_name))


async def upload_map_images(
    file_names: list[str], asset_dir: Path = MAP_ASSET_DIR
) -> list[str]:
    missing = [name for name in file_names if not (asset_dir / name).is_file()]
    if missing:
        raise FileNotFoundError(f"Missing map images in {asset_dir}: {missing}")
    return [
        await storage_client.upload_image(
            (asset_dir / name).read_bytes(),
            MAP_CONTENT_TYPE,
            map_object_key(name),
        )
        for name in file_names
    ]
