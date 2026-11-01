"""R2 object storage over the S3 API, with HTTP mocked via respx."""

import httpx
import pytest
import respx
from app.config import Settings, settings
from app.exceptions.turn_exceptions import SceneImageGenerationError
from app.integrations import storage_client
from app.integrations.s3_signing import sha256_hex
from pydantic import ValidationError

ENDPOINT = "https://acct.r2.cloudflarestorage.com"
BUCKET = "alpha-media"
PUBLIC_BASE = "https://media.example.test"
ACCESS_KEY = "AKEXAMPLE"
SECRET_KEY = "super-secret-value"
OBJECT_KEY = "scene-images/scene one.png"
OBJECT_URL = f"{ENDPOINT}/{BUCKET}/scene-images/scene%20one.png"
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
    assert url == f"{PUBLIC_BASE}/scene-images/scene one.png"
    assert request.content == CONTENT
    assert request.headers["Content-Type"] == "image/png"
    assert request.headers["x-amz-content-sha256"] == sha256_hex(CONTENT)
    assert f"Credential={ACCESS_KEY}/" in request.headers["Authorization"]
    assert SECRET_KEY not in str(request.headers)


@pytest.mark.asyncio
async def test_failed_upload_raises_the_domain_error_without_leaking_secrets() -> None:
    with respx.mock as router:
        router.put(OBJECT_URL).respond(403)
        with pytest.raises(SceneImageGenerationError) as raised:
            await storage_client.upload_image(CONTENT, "image/png", OBJECT_KEY)

    assert SECRET_KEY not in str(raised.value)


@pytest.mark.asyncio
async def test_network_failure_raises_the_domain_error() -> None:
    with respx.mock as router:
        router.put(OBJECT_URL).mock(side_effect=httpx.ConnectError("down"))
        with pytest.raises(SceneImageGenerationError):
            await storage_client.upload_image(CONTENT, "image/png", OBJECT_KEY)


@pytest.mark.asyncio
async def test_unconfigured_r2_falls_back_to_local_disk(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "r2_bucket_name", "")
    monkeypatch.setattr(settings, "local_upload_dir", str(tmp_path))

    url = await storage_client.upload_image(CONTENT, "image/png", "scene-images/a.png")

    assert url == "/uploads/scene-images/a.png"
    assert (tmp_path / "scene-images" / "a.png").read_bytes() == CONTENT


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
