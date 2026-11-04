"""Night Desk cover image: the shipped asset and the upload step."""

from pathlib import Path

import pytest
from app.config import settings
from scripts.night_desk.cover import COVER_PATH, upload_cover


def test_the_shipped_cover_exists() -> None:
    assert COVER_PATH.is_file()


async def test_upload_stores_the_cover_under_its_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(settings, "r2_bucket_name", "")
    monkeypatch.setattr(settings, "core_api_public_url", "http://localhost:8000")
    monkeypatch.setattr(settings, "local_upload_dir", str(tmp_path / "uploads"))
    cover = tmp_path / "cover.jpg"
    cover.write_bytes(b"jpeg-bytes")

    url = await upload_cover(cover)

    assert url == "http://localhost:8000/uploads/night-desk/cover.jpg"
    assert (
        tmp_path / "uploads" / "night-desk" / "cover.jpg"
    ).read_bytes() == b"jpeg-bytes"


async def test_upload_refuses_when_the_cover_is_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        await upload_cover(tmp_path / "absent.jpg")
