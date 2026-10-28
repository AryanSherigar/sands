"""AWS Signature Version 4 for S3-compatible object storage (Cloudflare R2).

Pure functions with no network access. The Turn Resolution Service keeps an
identical copy: services never import each other.
"""

from __future__ import annotations

import hashlib
import hmac
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import quote

ALGORITHM = "AWS4-HMAC-SHA256"
TERMINATOR = "aws4_request"
AMZ_DATE_FORMAT = "%Y%m%dT%H%M%SZ"
DATE_STAMP_FORMAT = "%Y%m%d"
HEADER_HOST = "host"
HEADER_CONTENT_SHA256 = "x-amz-content-sha256"
HEADER_AMZ_DATE = "x-amz-date"
HEADER_AUTHORIZATION = "Authorization"
PATH_SAFE_CHARACTERS = "/-_.~"


@dataclass(frozen=True)
class SigningCredentials:
    access_key_id: str
    secret_access_key: str
    region: str
    service: str


def quote_path(path: str) -> str:
    return quote(path, safe=PATH_SAFE_CHARACTERS)


def sha256_hex(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _hmac_sha256(key: bytes, message: str) -> bytes:
    return hmac.new(key, message.encode(), hashlib.sha256).digest()


def _signing_key(credentials: SigningCredentials, date_stamp: str) -> bytes:
    key = _hmac_sha256(f"AWS4{credentials.secret_access_key}".encode(), date_stamp)
    for part in (credentials.region, credentials.service, TERMINATOR):
        key = _hmac_sha256(key, part)
    return key


def _canonical_headers(headers: Mapping[str, str]) -> tuple[str, str]:
    normalized = {
        name.lower(): " ".join(value.split()) for name, value in headers.items()
    }
    names = sorted(normalized)
    block = "".join(f"{name}:{normalized[name]}\n" for name in names)
    return block, ";".join(names)


def _canonical_request(
    method: str,
    path: str,
    headers: Mapping[str, str],
    payload_hash: str,
) -> tuple[str, str]:
    header_block, signed_headers = _canonical_headers(headers)
    canonical_path = quote_path(path)
    request = "\n".join(
        [method, canonical_path, "", header_block, signed_headers, payload_hash]
    )
    return request, signed_headers


def build_authorization(
    method: str,
    path: str,
    headers: Mapping[str, str],
    payload_hash: str,
    moment: datetime,
    credentials: SigningCredentials,
) -> str:
    """Authorization header value for a request whose headers are all signed."""
    amz_date = moment.strftime(AMZ_DATE_FORMAT)
    date_stamp = moment.strftime(DATE_STAMP_FORMAT)
    scope = f"{date_stamp}/{credentials.region}/{credentials.service}/{TERMINATOR}"
    request, signed_headers = _canonical_request(method, path, headers, payload_hash)
    string_to_sign = "\n".join(
        [ALGORITHM, amz_date, scope, sha256_hex(request.encode())]
    )
    signature = hmac.new(
        _signing_key(credentials, date_stamp), string_to_sign.encode(), hashlib.sha256
    ).hexdigest()
    return (
        f"{ALGORITHM} Credential={credentials.access_key_id}/{scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )


def sign_request(
    method: str,
    host: str,
    path: str,
    content: bytes,
    credentials: SigningCredentials,
    moment: datetime | None = None,
) -> dict[str, str]:
    """Headers to send with a request for `path` carrying `content`."""
    moment = moment or datetime.now(timezone.utc)
    payload_hash = sha256_hex(content)
    signed = {
        HEADER_HOST: host,
        HEADER_CONTENT_SHA256: payload_hash,
        HEADER_AMZ_DATE: moment.strftime(AMZ_DATE_FORMAT),
    }
    authorization = build_authorization(
        method, path, signed, payload_hash, moment, credentials
    )
    return {
        HEADER_CONTENT_SHA256: payload_hash,
        HEADER_AMZ_DATE: signed[HEADER_AMZ_DATE],
        HEADER_AUTHORIZATION: authorization,
    }
