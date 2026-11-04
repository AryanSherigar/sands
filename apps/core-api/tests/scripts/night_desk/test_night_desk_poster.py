"""The lobby poster: the shipped asset, its URL and the upload step."""

import struct
from pathlib import Path

import pytest
from app.config import settings
from scripts.night_desk.poster import (
    POSTER_OBJECT_KEY,
    POSTER_PATH,
    poster_url,
    upload_poster,
)

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
POSTER_SIZE = (1080, 1528)


def _local_storage(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(settings, "r2_bucket_name", "")
    monkeypatch.setattr(settings, "core_api_public_url", "http://localhost:8000")
    monkeypatch.setattr(settings, "local_upload_dir", str(tmp_path / "uploads"))


def test_the_shipped_poster_is_a_portrait_png() -> None:
    header = POSTER_PATH.read_bytes()[:24]
    assert header.startswith(PNG_SIGNATURE)
    assert struct.unpack(">II", header[16:24]) == POSTER_SIZE


def test_the_shipped_product_shot_and_page_exist() -> None:
    poster_dir = POSTER_PATH.parent / "poster"
    assert (poster_dir / "truefeel_cabinet.jpg").is_file()
    assert "Because some things should be felt properly." in (
        poster_dir / "poster.html"
    ).read_text(encoding="utf-8")


def test_the_url_is_derived_from_the_object_key(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _local_storage(monkeypatch, tmp_path)
    assert poster_url() == f"http://localhost:8000/uploads/{POSTER_OBJECT_KEY}"


async def test_upload_stores_the_poster_under_its_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _local_storage(monkeypatch, tmp_path)
    poster = tmp_path / "poster.png"
    poster.write_bytes(b"png-bytes")

    url = await upload_poster(poster)

    assert url == poster_url()
    stored = tmp_path / "uploads" / "night-desk" / "truefeel-poster.png"
    assert stored.read_bytes() == b"png-bytes"


async def test_upload_refuses_when_the_poster_is_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        await upload_poster(tmp_path / "absent.png")


def test_a_dry_run_makes_no_network_call(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from app.integrations import storage_client

    from scripts import seed_night_desk

    async def refuse(*args: object, **kwargs: object) -> str:
        raise AssertionError("dry run must not upload")

    monkeypatch.setattr(storage_client, "upload_image", refuse)
    monkeypatch.setattr("sys.argv", ["seed_night_desk", "--dry-run"])

    seed_night_desk.main()

    assert "conditions=" in capsys.readouterr().out
