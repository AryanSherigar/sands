"""Purge accounts whose deletion grace period has expired.

Idempotent and safe to re-run; schedule it daily (e.g. a Cloud Run Job). Exits
non-zero when the run stopped early because memory kept failing.

Usage: python -m scripts.purge_deleted_accounts
"""

import asyncio
import sys

import structlog
from app.db.connection import close_db_connection, get_session_factory
from app.repositories.account_purge_repo import AccountPurgeRepo
from app.repositories.user_repo import UserRepo
from app.services.account_purge_service import AccountPurgeService, PurgeRunResult

logger = structlog.get_logger()

EXIT_OK = 0
EXIT_ABORTED = 1


async def _run() -> PurgeRunResult:
    async with get_session_factory()() as session:
        service = AccountPurgeService(
            session, AccountPurgeRepo(session), UserRepo(session)
        )
        return await service.purge_expired_accounts()


async def main() -> int:
    try:
        result = await _run()
        logger.info(
            "account_purge_finished",
            purged_count=result.purged,
            skipped_count=result.skipped,
            is_aborted=result.is_aborted,
        )
    finally:
        await close_db_connection()
    return EXIT_ABORTED if result.is_aborted else EXIT_OK


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
