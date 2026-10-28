"""Permanently removes accounts whose deletion grace period has expired."""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import structlog
from app.config import settings
from app.exceptions.memory_exceptions import MemoryPurgeError
from app.integrations import identity_client, memory_client, storage_client
from app.repositories.account_purge_repo import AccountPurgeRepo
from app.repositories.user_repo import UserRepo
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()

EVENT_ACCOUNT_PURGED = "account_purged"
EVENT_MEDIA_DELETE_FAILED = "account_purge_media_delete_failed"
EVENT_MEMORY_PURGE_FAILED = "memory_purge_failed"
EVENT_PURGE_ABORTED = "account_purge_aborted"


@dataclass(frozen=True)
class PurgeRunResult:
    purged: int = 0
    skipped: int = 0
    is_aborted: bool = False


class AccountPurgeService:
    def __init__(
        self, session: AsyncSession, purge_repo: AccountPurgeRepo, user_repo: UserRepo
    ) -> None:
        self.session = session
        self.purge_repo = purge_repo
        self.user_repo = user_repo

    async def purge_expired_accounts(
        self, now: datetime | None = None
    ) -> PurgeRunResult:
        """Purge every account past its grace period.

        Each user is purged and committed independently. A user whose memory purge
        fails is skipped, with their remaining product rows kept, and retried on
        the next run. The run stops early after
        `memory_purge_max_consecutive_failures` skips in a row.
        """
        cutoff = (now or datetime.now(UTC)) - timedelta(
            days=settings.account_deletion_grace_days
        )
        user_ids = await self.purge_repo.list_user_ids_due_for_purge(
            cutoff, settings.account_purge_user_limit
        )
        purged = skipped = consecutive_failures = 0
        for user_id in user_ids:
            if await self._try_purge_account(user_id):
                purged += 1
                consecutive_failures = 0
                continue
            skipped += 1
            consecutive_failures += 1
            if consecutive_failures >= settings.memory_purge_max_consecutive_failures:
                logger.error(EVENT_PURGE_ABORTED, purged=purged, skipped=skipped)
                return PurgeRunResult(purged, skipped, is_aborted=True)
        return PurgeRunResult(purged, skipped)

    async def _try_purge_account(self, user_id: uuid.UUID) -> bool:
        try:
            await self.purge_account(user_id)
        except MemoryPurgeError as error:
            logger.error(
                EVENT_MEMORY_PURGE_FAILED,
                user_id=str(user_id),
                code=error.code,
                upstream_status=error.upstream_status,
            )
            return False
        return True

    async def purge_account(self, user_id: uuid.UUID) -> None:
        """Delete a user's personal data and anonymise content others rely on.

        Memory is purged before the product rows it derives from; a
        MemoryPurgeError leaves the remaining rows in place for the next run.
        """
        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            return
        media_urls = [url for url in (user.avatar_url, user.banner_url) if url]
        await self._delete_playthroughs(user_id)
        await self._purge_scenario_memory(user_id)
        await self.purge_repo.delete_participations(user_id)
        media_urls += await self._remove_scenarios(user_id)
        await self.session.commit()
        await self._delete_media(media_urls)
        await identity_client.delete_identity(user.auth_provider_id)
        await self.purge_repo.delete_user(user_id)
        await self.session.commit()
        logger.info(EVENT_ACCOUNT_PURGED, user_id=str(user_id))

    async def _delete_playthroughs(self, user_id: uuid.UUID) -> None:
        while True:
            batch = await self.purge_repo.list_playthrough_ids(
                user_id, settings.account_purge_batch_size
            )
            if not batch:
                return
            await self.purge_repo.delete_outbox_rows(batch)
            await self.session.commit()
            await memory_client.purge(playthrough_ids=batch)
            await self.purge_repo.delete_playthroughs(batch)
            await self.session.commit()

    async def _purge_scenario_memory(self, user_id: uuid.UUID) -> None:
        scenario_ids = await self.purge_repo.list_deletable_scenario_ids(user_id)
        if scenario_ids:
            await memory_client.purge(scenario_ids=scenario_ids)

    async def _remove_scenarios(self, user_id: uuid.UUID) -> list[str]:
        await self.purge_repo.ensure_placeholder_user(settings.deleted_user_id)
        cover_urls = await self.purge_repo.list_deletable_scenario_cover_urls(user_id)
        await self.purge_repo.reassign_retained_scenarios(
            user_id, settings.deleted_user_id
        )
        await self.purge_repo.delete_music_generation_records(user_id)
        await self.purge_repo.delete_owned_scenarios(user_id)
        return cover_urls

    async def _delete_media(self, media_urls: list[str]) -> None:
        for url in media_urls:
            try:
                await storage_client.delete_object(url)
            # NOTE: best-effort; an orphaned object must not block the purge.
            except Exception:
                logger.warning(EVENT_MEDIA_DELETE_FAILED, url=url, exc_info=True)
