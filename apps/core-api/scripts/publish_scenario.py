"""Publish scenarios as their creator, through the real two-phase publish flow.

Run via:
    python -m scripts.publish_scenario --scenario-id <uuid> [--scenario-id <uuid> ...]

Phase one flips the draft to "publishing"; phase two runs the publish checks and
the memory template build, exactly as the publish endpoint's background task does.
Idempotent: an already published scenario is left untouched. Exits 1 when any
scenario is missing or fails to publish.
"""

import argparse
import asyncio
import sys
import uuid
from dataclasses import dataclass

from app.db.connection import AsyncSessionFactory, close_db_connection
from app.db.models.scenario import Scenario
from app.db.models.user import User
from app.exceptions.scenario_exceptions import ScenarioAlreadyPublishingError
from app.repositories.scenario_repo import ScenarioRepo
from app.services.publish_service import PublishService
from sqlalchemy.ext.asyncio import AsyncSession

EXIT_OK = 0
EXIT_FAILED = 1
PUBLISHED_STATUS = "published"
OUTCOME_ALREADY_PUBLISHED = "already published"
OUTCOME_MISSING = "missing"
OUTCOME_STARTED = "started"
OUTCOME_PUBLISHING = "already publishing"


@dataclass(frozen=True)
class PublishResult:
    scenario_id: uuid.UUID
    outcome: str
    detail: str | None = None

    @property
    def is_ok(self) -> bool:
        return self.outcome in (OUTCOME_ALREADY_PUBLISHED, PUBLISHED_STATUS)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario-id", type=uuid.UUID, action="append", required=True)
    return parser


def is_live(scenario: Scenario) -> bool:
    return scenario.status == PUBLISHED_STATUS and scenario.published_at is not None


async def start_publish(session: AsyncSession, scenario_id: uuid.UUID) -> PublishResult:
    scenario = await ScenarioRepo(session).get_by_id(scenario_id)
    if scenario is None:
        return PublishResult(scenario_id, OUTCOME_MISSING)
    if is_live(scenario):
        return PublishResult(scenario_id, OUTCOME_ALREADY_PUBLISHED)
    creator = await session.get(User, scenario.creator_id)
    try:
        await PublishService(ScenarioRepo(session)).start_publish(scenario_id, creator)
    except ScenarioAlreadyPublishingError:
        return PublishResult(scenario_id, OUTCOME_PUBLISHING)
    return PublishResult(scenario_id, OUTCOME_STARTED)


async def read_final_result(scenario_id: uuid.UUID) -> PublishResult:
    async with AsyncSessionFactory() as session:
        scenario = await ScenarioRepo(session).get_by_id(scenario_id)
    if scenario is not None and is_live(scenario):
        return PublishResult(scenario_id, PUBLISHED_STATUS)
    detail = scenario.publish_error if scenario is not None else None
    return PublishResult(scenario_id, "failed", detail)


async def publish_one(scenario_id: uuid.UUID) -> PublishResult:
    async with AsyncSessionFactory() as session:
        started = await start_publish(session, scenario_id)
    if started.outcome != OUTCOME_STARTED:
        return started
    await PublishService.run_publish_job(scenario_id, AsyncSessionFactory)
    return await read_final_result(scenario_id)


async def publish_all(scenario_ids: list[uuid.UUID]) -> list[PublishResult]:
    results = []
    try:
        for scenario_id in scenario_ids:
            result = await publish_one(scenario_id)
            print(f"{result.scenario_id}: {result.outcome} {result.detail or ''}")
            results.append(result)
    finally:
        await close_db_connection()
    return results


def main() -> int:
    args = build_parser().parse_args()
    results = asyncio.run(publish_all(args.scenario_id))
    return EXIT_OK if all(result.is_ok for result in results) else EXIT_FAILED


if __name__ == "__main__":
    sys.exit(main())
