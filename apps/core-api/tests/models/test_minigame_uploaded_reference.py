import pytest
from app.config import settings
from app.models.minigame import (
    _is_uploaded_audio_reference,
    _is_uploaded_image_reference,
)

R2_BASE = "https://media.example.test"
IMAGE_KEY = "scenario-maps/0a1b2c3d-0a1b-0a1b-0a1b-0a1b2c3d4e5f.png"
AUDIO_KEY = "scenario-audio/0a1b2c3d-0a1b-0a1b-0a1b-0a1b2c3d4e5f.mp3"


@pytest.fixture(autouse=True)
def r2_public_base(monkeypatch):
    monkeypatch.setattr(settings, "r2_public_base_url", R2_BASE)


def test_r2_urls_under_the_public_base_are_accepted():
    assert _is_uploaded_image_reference(f"{R2_BASE}/{IMAGE_KEY}")
    assert _is_uploaded_audio_reference(f"{R2_BASE}/{AUDIO_KEY}")


def test_a_public_base_with_a_path_prefix_is_honoured(monkeypatch):
    monkeypatch.setattr(settings, "r2_public_base_url", f"{R2_BASE}/media/")

    assert _is_uploaded_image_reference(f"{R2_BASE}/media/{IMAGE_KEY}")
    assert not _is_uploaded_image_reference(f"{R2_BASE}/{IMAGE_KEY}")


def test_other_hosts_are_rejected():
    assert not _is_uploaded_image_reference(f"https://evil.example.test/{IMAGE_KEY}")
    assert not _is_uploaded_image_reference(f"http://media.example.test/{IMAGE_KEY}")


def test_the_retired_gcs_host_is_no_longer_accepted():
    url = f"https://storage.googleapis.com/old-bucket/{IMAGE_KEY}"

    assert not _is_uploaded_image_reference(url)


def test_paths_that_are_not_uploads_are_rejected():
    assert not _is_uploaded_image_reference(f"{R2_BASE}/other/{IMAGE_KEY}")
    assert not _is_uploaded_image_reference(f"{R2_BASE}/{IMAGE_KEY}?x=1")
    assert not _is_uploaded_audio_reference(f"{R2_BASE}/{IMAGE_KEY}")


def test_nothing_remote_is_accepted_when_no_public_base_is_configured(monkeypatch):
    monkeypatch.setattr(settings, "r2_public_base_url", "")

    assert not _is_uploaded_image_reference(f"{R2_BASE}/{IMAGE_KEY}")
