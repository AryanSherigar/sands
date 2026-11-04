import pytest
from app.config import settings
from app.integrations import storage_client


def test_object_key_from_url_maps_local_uploads() -> None:
    url = f"{settings.core_api_public_url.rstrip('/')}/uploads/covers/a.png"

    assert storage_client.object_key_from_url(url) == "covers/a.png"


def test_object_key_from_url_ignores_foreign_urls() -> None:
    assert (
        storage_client.object_key_from_url("https://lh3.googleusercontent.com/x")
        is None
    )


@pytest.mark.asyncio
async def test_delete_object_removes_local_file_and_skips_foreign_urls(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "local_upload_dir", str(tmp_path))
    monkeypatch.setattr(settings, "r2_bucket_name", "")
    stored = tmp_path / "covers" / "a.png"
    stored.parent.mkdir(parents=True)
    stored.write_bytes(b"x")
    url = f"{settings.core_api_public_url.rstrip('/')}/uploads/covers/a.png"

    assert await storage_client.delete_object(url) is True
    assert not stored.exists()
    assert await storage_client.delete_object("https://example.com/a.png") is False
