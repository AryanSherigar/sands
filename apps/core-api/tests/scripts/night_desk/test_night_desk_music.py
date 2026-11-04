"""Night Desk tier music: hint wiring and the upload step."""

from pathlib import Path

import pytest
from app.config import settings
from app.services.display_hints import validate_display_hints
from scripts.night_desk import hints
from scripts.night_desk.music import find_missing_tracks, upload_tier_tracks

TIERS = ("uneasy", "tense", "dread", "breaking")


def _write_tracks(directory: Path, tiers: tuple[str, ...] = TIERS) -> None:
    for tier in tiers:
        (directory / f"{tier}.mp3").write_bytes(f"audio-{tier}".encode())


def test_every_tier_has_its_own_track_key() -> None:
    assert set(hints.TENSION_TRACKS) == set(TIERS)
    assert len(set(hints.TENSION_TRACKS.values())) == len(TIERS)


def test_tension_hint_declares_the_track_map() -> None:
    field = {
        "type": "enum",
        "options": list(TIERS),
        "initial": "uneasy",
        "display": hints.tension_hint(),
    }

    validate_display_hints({"tension_tier": field}, ["status_hud"])
    assert field["display"]["track_map"]["breaking"] == "night-desk-music/breaking.mp3"


def test_the_shipped_assets_cover_every_tier() -> None:
    assert find_missing_tracks() == []


def test_missing_tracks_are_listed(tmp_path: Path) -> None:
    _write_tracks(tmp_path, ("uneasy", "tense"))

    assert find_missing_tracks(tmp_path) == ["dread.mp3", "breaking.mp3"]


async def test_upload_stores_every_track_under_its_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(settings, "r2_bucket_name", "")
    monkeypatch.setattr(settings, "core_api_public_url", "http://localhost:8000")
    monkeypatch.setattr(settings, "local_upload_dir", str(tmp_path / "uploads"))
    _write_tracks(tmp_path)

    urls = await upload_tier_tracks(tmp_path)

    assert urls["dread"] == "http://localhost:8000/uploads/night-desk-music/dread.mp3"
    stored = tmp_path / "uploads" / "night-desk-music" / "dread.mp3"
    assert stored.read_bytes() == b"audio-dread"


async def test_upload_refuses_when_a_track_is_missing(tmp_path: Path) -> None:
    _write_tracks(tmp_path, ("uneasy",))

    with pytest.raises(FileNotFoundError):
        await upload_tier_tracks(tmp_path)
