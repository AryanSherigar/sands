"""Delete delivered memory outbox rows older than the retention window.

Undelivered rows and dead-lettered orphans are never deleted.

Usage: python -m scripts.prune_memory_outbox [--dry-run]
"""

import argparse
import asyncio

import structlog
from app.db.connection import close_db_connection, get_session_factory
from app.services.memory_outbox_prune_service import prune_delivered_outbox

logger = structlog.get_logger()

EVENT_PRUNE_FINISHED = "memory_outbox_prune_finished"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="count the rows that would be deleted without deleting them",
    )
    return parser.parse_args()


async def main() -> None:
    arguments = _parse_args()
    try:
        async with get_session_factory()() as session:
            result = await prune_delivered_outbox(session, arguments.dry_run)
        logger.info(
            EVENT_PRUNE_FINISHED,
            is_dry_run=result.is_dry_run,
            row_count=result.row_count,
        )
    finally:
        await close_db_connection()


if __name__ == "__main__":
    asyncio.run(main())
