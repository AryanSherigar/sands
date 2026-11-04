"""R2 object storage over the S3 API, with HTTP mocked via respx."""

import httpx
import pytest
import respx
from app.config import Settings, settings
from app.exceptions.upload_exceptions import UploadFailedError
from app.integrations import storage_client
from app.integrations.s3_signing import sha256_hex
from pydantic import ValidationError

ENDPOINT = "https://acct.r2.cloudflarestorage.com"
BUCKET = "alpha-media"
PUBLIC_BASE = "https://media.example.test"
ACCESS_KEY = "AKEXAMPLE"
SECRET_KEY = "super-secret-value"
OBJECT_KEY = "scenario-covers/cover one.png"
OBJECT_URL = f"{ENDPOINT}/{BUCKET}/scenario-covers/cover%20one.png"
CONTENT = b"png-bytes"
SECRET_KEY_FOR_APP = "x" * 64


@pytest.fixture(autouse=True)
def r2_settings(monkeypatch):
    monkeypatch.setattr(settings, "environment", "testing")
    monkeypatch.setattr(settings, "r2_account_id", "acct")
    monkeypatch.setattr(settings, "r2_endpoint_url", "")
    monkeypatch.setattr(settings, "r2_access_key_id", ACCESS_KEY)
    monkeypatch.setattr(settings, "r2_secret_access_key", SECRET_KEY)
    monkeypatch.setattr(settings, "r2_bucket_name", BUCKET)
    monkeypatch.setattr(settings, "r2_public_base_url", PUBLIC_BASE)
    monkeypatch.setattr(storage_client, "_http_client", None)
    yield
    monkeypatch.setattr(storage_client, "_http_client", None)


@pytest.mark.asyncio
async def test_upload_puts_the_signed_object_and_returns_its_public_url() -> None:
    with respx.mock as router:
        route = router.put(OBJECT_URL).respond(200)
        url = await storage_client.upload_image(CONTENT, "image/png", OBJECT_KEY)

    request = route.calls[0].request
    assert url == f"{PUBLIC_BASE}/scenario-covers/cover one.png"
    assert request.content == CONTENT
    assert request.headers["Content-Type"] == "image/png"
    assert request.headers["x-amz-content-sha256"] == sha256_hex(CONTENT)
    assert f"Credential={ACCESS_KEY}/" in request.headers["Authorization"]
    assert "/auto/s3/aws4_request" in request.headers["Authorization"]
    assert SECRET_KEY not in str(request.headers)


@pytest.mark.asyncio
async def test_failed_upload_raises_the_domain_error_without_leaking_secrets() -> None:
    with respx.mock as router:
        router.put(OBJECT_URL).respond(403)
        with pytest.raises(UploadFailedError) as raised:
            await storage_client.upload_image(CONTENT, "image/png", OBJECT_KEY)

    assert SECRET_KEY not in str(raised.value)


@pytest.mark.asyncio
async def test_network_failure_raises_the_domain_error() -> None:
    with respx.mock as router:
        router.put(OBJECT_URL).mock(side_effect=httpx.ConnectError("down"))
        with pytest.raises(UploadFailedError):
            await storage_client.upload_image(CONTENT, "image/png", OBJECT_KEY)


def test_public_url_uses_the_r2_public_base() -> None:
    assert (
        storage_client.public_url_for("default-music/triumph.mp3")
        == f"{PUBLIC_BASE}/default-music/triumph.mp3"
    )


def test_object_key_is_recovered_from_an_r2_public_url() -> None:
    url = f"{PUBLIC_BASE}/scenario-covers/a.png"

    assert storage_client.object_key_from_url(url) == "scenario-covers/a.png"
    assert storage_client.object_key_from_url("https://elsewhere.test/a.png") is None


@pytest.mark.asyncio
async def test_delete_removes_the_remote_object() -> None:
    with respx.mock as router:
        route = router.delete(f"{ENDPOINT}/{BUCKET}/scenario-covers/a.png").respond(204)
        deleted = await storage_client.delete_object(
            f"{PUBLIC_BASE}/scenario-covers/a.png"
        )

    assert deleted is True
    assert route.called


@pytest.mark.asyncio
async def test_deleting_a_missing_object_counts_as_success() -> None:
    with respx.mock as router:
        router.delete(f"{ENDPOINT}/{BUCKET}/scenario-covers/a.png").respond(404)
        deleted = await storage_client.delete_object(
            f"{PUBLIC_BASE}/scenario-covers/a.png"
        )

    assert deleted is True


@pytest.mark.asyncio
async def test_other_delete_failures_propagate() -> None:
    with respx.mock as router:
        router.delete(f"{ENDPOINT}/{BUCKET}/scenario-covers/a.png").respond(403)
        with pytest.raises(httpx.HTTPStatusError):
            await storage_client.delete_object(f"{PUBLIC_BASE}/scenario-covers/a.png")


@pytest.mark.asyncio
async def test_foreign_urls_are_never_deleted() -> None:
    with respx.mock:
        assert (
            await storage_client.delete_object("https://elsewhere.test/a.png") is False
        )


@pytest.mark.asyncio
async def test_unconfigured_r2_falls_back_to_local_disk(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "r2_bucket_name", "")
    monkeypatch.setattr(settings, "local_upload_dir", str(tmp_path))

    url = await storage_client.upload_image(CONTENT, "image/png", "covers/a.png")

    assert url.endswith("/uploads/covers/a.png")
    assert (tmp_path / "covers" / "a.png").read_bytes() == CONTENT


def test_production_refuses_to_boot_without_r2() -> None:
    with pytest.raises(ValidationError, match="R2"):
        Settings(
            _env_file=None, environment="production", secret_key=SECRET_KEY_FOR_APP
        )


def test_production_boots_with_r2_configured() -> None:
    config = Settings(
        _env_file=None,
        environment="production",
        secret_key=SECRET_KEY_FOR_APP,
        r2_account_id="acct",
        r2_access_key_id=ACCESS_KEY,
        r2_secret_access_key=SECRET_KEY,
        r2_bucket_name=BUCKET,
        r2_public_base_url=PUBLIC_BASE,
    )

    assert config.is_r2_configured is True
    assert config.r2_endpoint == ENDPOINT
