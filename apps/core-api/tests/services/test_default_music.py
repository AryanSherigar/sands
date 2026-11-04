"""Unit tests for the built-in default mood track resolution."""

from app.config import settings
from app.db.models.scenario_music import MOOD_SLOTS
from app.services import default_music


def test_all_default_track_urls_covers_every_mood():
    urls = default_music.all_default_track_urls()
    assert set(urls) == set(MOOD_SLOTS)
    assert all(urls[mood] for mood in MOOD_SLOTS)


def test_default_track_url_uses_local_upload_path_in_development(monkeypatch):
    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(settings, "r2_bucket_name", "")
    monkeypatch.setattr(settings, "core_api_public_url", "http://localhost:8000")

    assert default_music.default_track_url("peaceful") == (
        "http://localhost:8000/uploads/default-music/peaceful.mp3"
    )


def test_default_track_url_uses_the_r2_public_url_in_production(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "r2_access_key_id", "key")
    monkeypatch.setattr(settings, "r2_secret_access_key", "secret")
    monkeypatch.setattr(settings, "r2_account_id", "acct")
    monkeypatch.setattr(settings, "r2_bucket_name", "sands-prod-bucket")
    monkeypatch.setattr(settings, "r2_public_base_url", "https://media.example.test/")

    assert default_music.default_track_url("triumph") == (
        "https://media.example.test/default-music/triumph.mp3"
    )
