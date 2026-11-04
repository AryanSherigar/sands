"""Build memory templates for every published scenario.

Idempotent: a second run against unchanged content creates nothing. A scenario
whose authored content changed since its last publish is reported as
skipped_drift; republish it to get a new revision.

Usage: python -m scripts.rebuild_memory_templates [--dry-run]
"""

import argparse
import asyncio
from collections import Counter

import structlog
from app.db.connection import close_db_connection, get_session_factory
from app.services.memory_template_rebuild_service import rebuild_all_templates

logger = structlog.get_logger()

EVENT_REBUILD_FINISHED = "memory_template_rebuild_finished"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="list the scenarios that would be built without calling memory",
    )
    return parser.parse_args()


async def main() -> None:
    arguments = _parse_args()
    try:
        async with get_session_factory()() as session:
            results = await rebuild_all_templates(session, arguments.dry_run)
        counts = Counter(result.status for result in results)
        logger.info(
            EVENT_REBUILD_FINISHED,
            is_dry_run=arguments.dry_run,
            scenario_count=len(results),
            counts=dict(counts),
        )
    finally:
        await close_db_connection()


if __name__ == "__main__":
    asyncio.run(main())
