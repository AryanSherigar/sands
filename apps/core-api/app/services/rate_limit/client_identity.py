"""Resolve who a request is for rate-limit keying, without a database hit.

The user id comes from a signature-verified access token only; an invalid
token falls back to the client IP and real authentication still happens in
get_current_user. The client IP is read from X-Forwarded-For at a fixed
distance from the right, because every entry left of the trusted proxies is
client-supplied and spoofable.
"""

import uuid
from dataclasses import dataclass

import jwt
from app.config import settings
from fastapi import Request

HEADER_FORWARDED_FOR = "X-Forwarded-For"
HEADER_AUTHORIZATION = "Authorization"
HEADER_DEV_USER_ID = "x-dev-user-id"
BEARER_PREFIX = "Bearer "
ACCESS_TOKEN_TYPE = "access"
DEV_ENVIRONMENTS = frozenset({"development", "testing"})
UNKNOWN_CLIENT_IP = "unknown"


@dataclass(frozen=True)
class ClientIdentity:
    user_id: uuid.UUID | None
    ip: str

    @property
    def is_authenticated(self) -> bool:
        return self.user_id is not None


def resolve_client_ip(request: Request) -> str:
    hops = settings.trusted_proxy_hops
    if hops <= 0:
        return request.client.host if request.client else UNKNOWN_CLIENT_IP
    forwarded = request.headers.get(HEADER_FORWARDED_FOR, "")
    entries = [entry.strip() for entry in forwarded.split(",") if entry.strip()]
    if len(entries) < hops:
        return request.client.host if request.client else UNKNOWN_CLIENT_IP
    return entries[-hops]


def _parse_uuid(value: str | None) -> uuid.UUID | None:
    if not value:
        return None
    try:
        return uuid.UUID(value)
    except ValueError:
        return None


def _user_id_from_token(token: str) -> uuid.UUID | None:
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.jwt_algorithm]
        )
    except jwt.InvalidTokenError:
        return None
    if payload.get("type") != ACCESS_TOKEN_TYPE:
        return None
    return _parse_uuid(payload.get("sub"))


def resolve_user_id(request: Request) -> uuid.UUID | None:
    if settings.environment in DEV_ENVIRONMENTS:
        dev_user_id = _parse_uuid(request.headers.get(HEADER_DEV_USER_ID))
        if dev_user_id:
            return dev_user_id
    authorization = request.headers.get(HEADER_AUTHORIZATION, "")
    if not authorization.startswith(BEARER_PREFIX):
        return None
    return _user_id_from_token(authorization.removeprefix(BEARER_PREFIX))


def resolve_client_identity(request: Request) -> ClientIdentity:
    return ClientIdentity(
        user_id=resolve_user_id(request), ip=resolve_client_ip(request)
    )
