"""Purge memory scopes that Core no longer knows about.

Dry-run by default: lists the orphan playthroughs and scenarios and changes
nothing. Scopes younger than the minimum age are never orphans. With --apply
the script refuses to run when Core reports no live ids while memory holds
scopes, or when the orphans are over half of memory's scopes (--force overrides
only the second check). Exits non-zero when it aborts.

Usage: python -m scripts.reconcile_memory_orphans [--apply] [--force]
"""

import argparse
import asyncio
import sys

import structlog
from app.db.connection import close_db_connection, get_session_factory
from app.services.memory_reconcile_service import reconcile_memory_orphans

logger = structlog.get_logger()

EVENT_RECONCILE_FINISHED = "memory_reconcile_finished"
EXIT_OK = 0
EXIT_ABORTED = 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply", action="store_true", help="purge the orphans (default: dry-run)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="allow purging more than half of memory's scopes",
    )
    return parser.parse_args()


async def main() -> int:
    arguments = _parse_args()
    try:
        async with get_session_factory()() as session:
            result = await reconcile_memory_orphans(
                session, arguments.apply, arguments.force
            )
        logger.info(
            EVENT_RECONCILE_FINISHED,
            status=result.status,
            reason=result.reason,
            orphan_count=result.plan.orphan_count,
        )
    finally:
        await close_db_connection()
    return EXIT_ABORTED if result.status == "aborted" else EXIT_OK


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
