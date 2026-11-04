"""One-time script: upload the premade animated avatars to storage.

Run once per environment (dev/staging/prod) and again whenever a premade avatar
changes. Expects `<slug>.mavatar` and `<slug>.webp` for every entry in
app/services/premade_avatars.py in the given directory (the repo's
`premade-avatars/` folder).

Usage: python -m scripts.seed_premade_avatars /path/to/premade-avatars
"""

import asyncio
import sys
from pathlib import Path

from app.integrations import storage_client
from app.services import premade_avatars
from app.services.premade_avatars import PremadeAvatarEntry

_AVATAR_CONTENT_TYPE = "application/zip"
_PREVIEW_CONTENT_TYPE = "image/webp"


async def _upload(source_dir: Path, object_key: str, content_type: str) -> str:
    source_file = source_dir / Path(object_key).name
    if not source_file.is_file():
        raise FileNotFoundError(f"Missing {source_file.name} in {source_dir}")
    url = await storage_client.upload_image(
        source_file.read_bytes(), content_type, object_key
    )
    expected_url = storage_client.public_url_for(object_key)
    if url != expected_url:
        raise RuntimeError(
            f"Uploaded URL {url} does not match canonical {expected_url}"
        )
    return url


async def _seed_entry(source_dir: Path, entry: PremadeAvatarEntry) -> None:
    avatar_url = await _upload(
        source_dir, premade_avatars.avatar_object_key(entry), _AVATAR_CONTENT_TYPE
    )
    await _upload(
        source_dir, premade_avatars.preview_object_key(entry), _PREVIEW_CONTENT_TYPE
    )
    print(f"Seeded {entry.slug}: {avatar_url}")


async def _seed_all(source_dir: Path) -> None:
    for entry in premade_avatars.PREMADE_AVATARS:
        await _seed_entry(source_dir, entry)


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python -m scripts.seed_premade_avatars /path/to/premade-avatars")
        sys.exit(1)
    source_dir = Path(sys.argv[1])
    if not source_dir.is_dir():
        print(f"Not a directory: {source_dir}")
        sys.exit(1)
    asyncio.run(_seed_all(source_dir))


if __name__ == "__main__":
    main()
