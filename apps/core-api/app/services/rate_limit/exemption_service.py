"""Admin exemption lookup (user id -> Firebase UID) for per-user burst limits.

Cached in-process so the burst middleware doesn't add a user lookup to every
request; a UID removed from config keeps its exemption for at most the TTL.
"""

import time
import uuid
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

from app.config import settings
from app.repositories.user_repo import UserRepo
from sqlalchemy.ext.asyncio import AsyncSession

SessionContextFactory = Callable[[], AbstractAsyncContextManager[AsyncSession]]

_cache: dict[uuid.UUID, tuple[bool, float]] = {}


def clear_exemption_cache() -> None:
    _cache.clear()


class ExemptionService:
    def __init__(self, session_factory: SessionContextFactory) -> None:
        self._session_factory = session_factory

    async def is_exempt_user(self, user_id: uuid.UUID) -> bool:
        exempt_uids = settings.exempt_firebase_uids
        if not exempt_uids:
            return False
        cached = _cache.get(user_id)
        now = time.monotonic()
        if cached and cached[1] > now:
            return cached[0]
        is_exempt = await self._lookup(user_id, exempt_uids)
        _cache[user_id] = (is_exempt, now + settings.rate_limit_exempt_cache_seconds)
        return is_exempt

    async def _lookup(self, user_id: uuid.UUID, exempt_uids: frozenset[str]) -> bool:
        async with self._session_factory() as session:
            user = await UserRepo(session).get_by_id(user_id)
        return user is not None and user.auth_provider_id in exempt_uids
