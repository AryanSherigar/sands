"""Object storage client for Turn Resolution Service.

Only module in this service that talks to object storage (Cloudflare R2, over
its S3 API). TRS gets its own copy of core-api's storage_client.py rather than
calling core-api's upload endpoint mid-turn -- that would add a blocking
inter-service HTTP hop to an already-synchronous pipeline. Both services write
into the same physical bucket in production; object storage isn't a
per-service-owned boundary the way the database is. In development, or whenever
R2 is not configured, objects are written to a local directory.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from urllib.parse import urlparse

import httpx
import structlog
from app.config import settings
from app.exceptions.turn_exceptions import SceneImageGenerationError
from app.integrations.s3_signing import (
    SigningCredentials,
    quote_path,
    sign_request,
)

logger = structlog.get_logger()

HTTP_METHOD_PUT = "PUT"
S3_SERVICE_NAME = "s3"

_http_client: httpx.AsyncClient | None = None


def _is_local_storage() -> bool:
    return settings.environment == "development" or not settings.is_r2_configured


def _get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(
            base_url=settings.r2_endpoint,
            timeout=settings.r2_request_timeout_seconds,
        )
    return _http_client


def _credentials() -> SigningCredentials:
    return SigningCredentials(
        access_key_id=settings.r2_access_key_id,
        secret_access_key=settings.r2_secret_access_key,
        region=settings.r2_region,
        service=S3_SERVICE_NAME,
    )


async def _put_object(content: bytes, content_type: str, object_key: str) -> None:
    path = f"/{settings.r2_bucket_name}/{object_key}"
    host = urlparse(settings.r2_endpoint).netloc
    headers = sign_request(HTTP_METHOD_PUT, host, path, content, _credentials())
    headers["Content-Type"] = content_type
    response = await _get_http_client().put(
        quote_path(path), content=content, headers=headers
    )
    response.raise_for_status()


def _save_local_sync(content: bytes, object_key: str) -> str:
    dest_path = Path(settings.local_upload_dir) / object_key
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_bytes(content)
    return f"/uploads/{object_key}"


async def upload_image(content: bytes, content_type: str, object_key: str) -> str:
    """Upload bytes to local storage in dev or R2 in production; return public URL."""
    try:
        if _is_local_storage():
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(
                None, _save_local_sync, content, object_key
            )
        await _put_object(content, content_type, object_key)
    except (httpx.HTTPError, OSError) as exc:
        raise SceneImageGenerationError(f"Failed to upload scene image: {exc}") from exc
    return f"{settings.r2_public_base_url.rstrip('/')}/{object_key}"
