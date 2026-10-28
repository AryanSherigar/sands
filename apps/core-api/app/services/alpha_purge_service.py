"""Deletes closed-alpha data and tester accounts once retention has ended."""

import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta

import structlog
from app.exceptions.alpha_exceptions import AlphaRetentionNotReachedError
from app.exceptions.memory_exceptions import MemoryPurgeError
from app.logging_config import log_audit_event
from app.repositories.alpha_purge_repo import AlphaPurgeRepo
from app.services.account_purge_service import AccountPurgeService
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()

EVENT_ALPHA_PURGE_PLANNED = "alpha_purge_planned"
EVENT_ALPHA_PURGE_ACCOUNT_FAILED = "alpha_purge_account_failed"
EVENT_ALPHA_DATA_PURGED = "alpha_data_purged"
DEFAULT_RETENTION_DAYS = 90


@dataclass(frozen=True)
class AlphaPurgePlan:
    retention_date: date
    tester_user_ids: list[uuid.UUID]
    row_counts: dict[str, int]


@dataclass
class AlphaPurgeOutcome:
    purged_accounts: int = 0
    failed_user_ids: list[uuid.UUID] = field(default_factory=list)


class AlphaPurgeService:
    def __init__(
        self,
        session: AsyncSession,
        repo: AlphaPurgeRepo,
        account_purge: AccountPurgeService,
    ) -> None:
        self._session = session
        self._repo = repo
        self._account_purge = account_purge

    async def plan(
        self, ended_on: date, retention_days: int, today: date
    ) -> AlphaPurgePlan:
        """Raises AlphaRetentionNotReachedError before the retention date."""
        retention_date = ended_on + timedelta(days=retention_days)
        if today < retention_date:
            raise AlphaRetentionNotReachedError(retention_date.isoformat())
        user_ids = await self._repo.list_tester_user_ids()
        counts = await self._repo.count_alpha_rows(user_ids) if user_ids else {}
        logger.info(
            EVENT_ALPHA_PURGE_PLANNED,
            tester_count=len(user_ids),
            row_counts=counts,
        )
        return AlphaPurgePlan(retention_date, user_ids, counts)

    async def apply(self, plan: AlphaPurgePlan) -> AlphaPurgeOutcome:
        """Delete the alpha rows, then every tester account, one account at a time.

        An account whose memory purge fails is kept and reported so the run can
        be repeated; its alpha rows are already gone."""
        outcome = AlphaPurgeOutcome()
        if plan.tester_user_ids:
            await self._repo.delete_alpha_rows(plan.tester_user_ids)
            await self._session.commit()
        for user_id in plan.tester_user_ids:
            if await self._try_purge(user_id):
                outcome.purged_accounts += 1
            else:
                outcome.failed_user_ids.append(user_id)
        log_audit_event(
            logger,
            EVENT_ALPHA_DATA_PURGED,
            purged_count=outcome.purged_accounts,
            failed_count=len(outcome.failed_user_ids),
        )
        return outcome

    async def _try_purge(self, user_id: uuid.UUID) -> bool:
        try:
            await self._account_purge.purge_account(user_id)
        except MemoryPurgeError as error:
            logger.error(
                EVENT_ALPHA_PURGE_ACCOUNT_FAILED,
                user_id=str(user_id),
                code=error.code,
            )
            return False
        return True
