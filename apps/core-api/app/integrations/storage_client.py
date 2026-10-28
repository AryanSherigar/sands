"""Object storage client for Core API.

Only module that talks to object storage (Cloudflare R2, over its S3 API) --
nowhere else in the codebase should call it. In development, or whenever R2 is
not configured, objects are written to a local directory served at /uploads.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from urllib.parse import urlparse

import httpx
from app.config import settings
from app.exceptions.upload_exceptions import UploadFailedError
from app.integrations.s3_signing import (
    SigningCredentials,
    quote_path,
    sign_request,
)

logger = logging.getLogger(__name__)

HTTP_METHOD_PUT = "PUT"
HTTP_METHOD_DELETE = "DELETE"
HTTP_STATUS_NOT_FOUND = 404
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


async def close_storage_client() -> None:
    global _http_client
    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None


def _credentials() -> SigningCredentials:
    return SigningCredentials(
        access_key_id=settings.r2_access_key_id,
        secret_access_key=settings.r2_secret_access_key,
        region=settings.r2_region,
        service=S3_SERVICE_NAME,
    )


async def _send_object_request(
    method: str, object_key: str, content: bytes = b"", content_type: str | None = None
) -> None:
    path = f"/{settings.r2_bucket_name}/{object_key}"
    host = urlparse(settings.r2_endpoint).netloc
    headers = sign_request(method, host, path, content, _credentials())
    if content_type:
        headers["Content-Type"] = content_type
    response = await _get_http_client().request(
        method, quote_path(path), content=content, headers=headers
    )
    response.raise_for_status()


def _local_url(object_key: str) -> str:
    base_url = settings.core_api_public_url.rstrip("/")
    return f"{base_url}/uploads/{object_key}"


def _r2_url(object_key: str) -> str:
    return f"{settings.r2_public_base_url.rstrip('/')}/{object_key}"


def _save_local_sync(content: bytes, object_key: str) -> str:
    dest_path = Path(settings.local_upload_dir) / object_key
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_bytes(content)
    return _local_url(object_key)


def public_url_for(object_key: str) -> str:
    """Compute the deterministic public URL for an object key already stored
    out of band (e.g. a seeded built-in default asset), without uploading
    anything."""
    return _local_url(object_key) if _is_local_storage() else _r2_url(object_key)


async def upload_image(content: bytes, content_type: str, object_key: str) -> str:
    """Upload bytes to local storage in dev or R2 in production; return public URL."""
    try:
        if _is_local_storage():
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(
                None, _save_local_sync, content, object_key
            )
        await _send_object_request(HTTP_METHOD_PUT, object_key, content, content_type)
    except (httpx.HTTPError, OSError) as exc:
        raise UploadFailedError(f"Failed to upload image: {exc}") from exc
    return _r2_url(object_key)


async def upload_public_bytes(
    object_key: str, content: bytes, content_type: str = "application/octet-stream"
) -> str:
    """Upload arbitrary bytes to public object storage; return public URL."""
    return await upload_image(content=content, content_type=content_type, object_key=object_key)


def object_key_from_url(url: str) -> str | None:
    """Map a URL this service produced back to its object key, or None for
    URLs it does not own (e.g. an external avatar host)."""
    prefixes = [f"{settings.core_api_public_url.rstrip('/')}/uploads/"]
    if settings.r2_public_base_url:
        prefixes.append(f"{settings.r2_public_base_url.rstrip('/')}/")
    for prefix in prefixes:
        if url.startswith(prefix):
            return url[len(prefix) :]
    return None


def _delete_local_sync(object_key: str) -> None:
    (Path(settings.local_upload_dir) / object_key).unlink(missing_ok=True)


async def delete_object(url: str) -> bool:
    """Delete the stored object behind a URL this service produced.

    Returns False when the URL is not ours, so callers never delete
    third-party or unknown assets. Deleting an object that is already gone
    counts as success.
    """
    object_key = object_key_from_url(url)
    if object_key is None:
        return False
    if _is_local_storage():
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _delete_local_sync, object_key)
        return True
    try:
        await _send_object_request(HTTP_METHOD_DELETE, object_key)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code != HTTP_STATUS_NOT_FOUND:
            raise
        logger.info("Object already deleted: %s", object_key)
    return True
