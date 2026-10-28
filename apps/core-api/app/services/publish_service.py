"""Publish flow orchestration: content-tag check + memory template build.

Publish is two-phase: `start_publish` runs synchronously within the request
(validates + flips the scenario to 'publishing'), and `run_publish_job` runs
afterwards as a FastAPI BackgroundTask against its own DB session, since the
request-scoped session is gone by the time it executes.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog
from app.db.models.scenario import Scenario
from app.db.models.user import User
from app.exceptions.map_exceptions import MapPublishValidationError
from app.exceptions.scenario_exceptions import (
    ScenarioAccessDeniedError,
    ScenarioAlreadyPublishingError,
    ScenarioNotFoundError,
    ScenarioValidationError,
)
from app.logging_config import log_audit_event
from app.models.content_tags import validate_content_tags
from app.repositories.entity_repo import EntityRepo
from app.repositories.fact_repo import FactRepo
from app.repositories.map_repo import MapRepo
from app.repositories.scenario_repo import ScenarioRepo
from app.services.achievement_service import build_achievement_service
from app.services.memory_template_service import push_template
from app.services.rate_limit.policies import QuotaFeature
from app.services.rate_limit.quota_service import QuotaService, quota_scope
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from strategy_contracts.publish_checks import check_publishable
from strategy_contracts.scenario import StrategyScenario

logger = structlog.get_logger()

ALLOWED_CONTENT_TAGS: set[str] = {"all-ages", "teen", "mature"}

NEWBIE_MODE = "newbie"
STRATEGY_MODE = "strategy"
LEGACY_OPENING_PROMPT_KEY = "openingPrompt"

EVENT_SCENARIO_PUBLISH_STARTED = "scenario_publish_started"
EVENT_SCENARIO_PUBLISH_COMPLETED = "scenario_publish_completed"
EVENT_SCENARIO_PUBLISH_FAILED = "scenario_publish_failed"

# NOTE: Failures the creator caused and can fix keep their publish unit spent;
# anything else (memory outage, timeouts, template rejections) is refunded.
USER_CAUSED_PUBLISH_ERRORS = (ScenarioValidationError, MapPublishValidationError)


class PublishService:
    """Service orchestrating the two-phase publish flow."""

    def __init__(
        self, scenario_repo: ScenarioRepo, quota_service: QuotaService | None = None
    ) -> None:
        self.scenario_repo = scenario_repo
        self.quota_service = quota_service

    async def start_publish(self, scenario_id: uuid.UUID, user: User) -> Scenario:
        """Validate ownership, take a publish unit, and flip to 'publishing'."""
        scenario = await self.scenario_repo.get_by_id_for_update(scenario_id)
        if not scenario or scenario.status == "archived":
            raise ScenarioNotFoundError()

        if scenario.creator_id != user.user_id:
            raise ScenarioAccessDeniedError()

        if scenario.status == "publishing":
            raise ScenarioAlreadyPublishingError()

        async with quota_scope(self.quota_service, QuotaFeature.PUBLISH, user):
            return await self._flip_to_publishing(scenario, user.user_id)

    async def _flip_to_publishing(
        self, scenario: Scenario, user_id: uuid.UUID
    ) -> Scenario:
        scenario_id = scenario.scenario_id
        scenario.status = "publishing"
        scenario.publish_error = None
        updated = await self.scenario_repo.update(scenario)
        log_audit_event(
            logger,
            EVENT_SCENARIO_PUBLISH_STARTED,
            scenario_id=str(scenario_id),
            user_id=str(user_id),
        )
        # NOTE: Must commit here rather than leaving it to the request-scoped
        # session's usual end-of-request commit: FastAPI runs BackgroundTasks
        # *before* a yield-dependency's post-yield cleanup code (including
        # get_db_session's commit) executes. Without an explicit commit now,
        # this row's UPDATE stays uncommitted (holding its row lock) while
        # run_publish_job's own session blocks trying to UPDATE the same
        # row — a deadlock between this request and the background job.
        await self.scenario_repo.session.commit()
        return updated

    @staticmethod
    async def run_publish_job(
        scenario_id: uuid.UUID,
        session_factory: async_sessionmaker[AsyncSession],
        quota_service: QuotaService | None = None,
    ) -> None:
        """Run the content-tag check and the memory template build in the background."""
        async with session_factory() as session:
            scenario = await ScenarioRepo(session).get_by_id(scenario_id)
            if scenario is None:
                return
            await _attempt_publish(session, scenario, quota_service)
            await session.commit()

            if scenario.status == "published":
                achievements = build_achievement_service(session)
                await achievements.evaluate_and_award(
                    scenario.creator_id, datetime.now(UTC)
                )
                await session.commit()


async def _attempt_publish(
    session: AsyncSession, scenario: Scenario, quota_service: QuotaService | None
) -> None:
    content_edited_at_at_job_start = scenario.content_edited_at
    publish_started_at = scenario.updated_at
    next_revision = scenario.publish_revision + 1
    try:
        await _validate_and_build_template(session, scenario, next_revision)
    # NOTE: Intentionally broad. This is the terminal handler for the
    # background publish job -- there is no other error path once we
    # reach here, and narrowing risks an unanticipated exception type
    # propagating unhandled, leaving the scenario stuck in
    # "publishing" status forever instead of being marked
    # publish_failed with a visible error message.
    except Exception as exc:  # noqa: BLE001 - captured for publish_error
        _mark_publish_failed(scenario, exc)
        if quota_service and not isinstance(exc, USER_CAUSED_PUBLISH_ERRORS):
            await quota_service.refund_for(
                QuotaFeature.PUBLISH, scenario.creator_id, publish_started_at
            )
        return
    _mark_publish_succeeded(scenario, content_edited_at_at_job_start, next_revision)
    log_audit_event(
        logger,
        EVENT_SCENARIO_PUBLISH_COMPLETED,
        scenario_id=str(scenario.scenario_id),
    )


async def _validate_and_build_template(
    session: AsyncSession, scenario: Scenario, next_revision: int
) -> None:
    _check_content_tag(scenario)
    _check_content_tags(scenario)
    _check_newbie_minimum(scenario)
    _check_strategy_document(scenario)
    await _check_map_start_pin(scenario, MapRepo(session))
    if scenario.mode == STRATEGY_MODE:
        return
    await push_template(
        scenario,
        next_revision,
        EntityRepo(session),
        FactRepo(session),
        MapRepo(session),
    )


def _mark_publish_succeeded(
    scenario: Scenario, content_edited_at_at_job_start: datetime, next_revision: int
) -> None:
    scenario.status = "published"
    scenario.publish_revision = next_revision
    scenario.published_at = scenario.published_at or datetime.now(UTC)
    scenario.published_content_edited_at = content_edited_at_at_job_start
    scenario.publish_error = None


def _mark_publish_failed(scenario: Scenario, exc: Exception) -> None:
    scenario.status = "draft" if scenario.published_at is None else "publish_failed"
    scenario.publish_error = str(exc)
    log_audit_event(
        logger,
        EVENT_SCENARIO_PUBLISH_FAILED,
        scenario_id=str(scenario.scenario_id),
        error=str(exc),
    )


def _check_content_tag(scenario: Scenario) -> None:
    """Validate the creator-declared content tag against the fixed taxonomy."""
    if not scenario.content_tag or scenario.content_tag not in ALLOWED_CONTENT_TAGS:
        raise ScenarioValidationError(
            f"content_tag must be one of {sorted(ALLOWED_CONTENT_TAGS)}, "
            f"got {scenario.content_tag!r}"
        )


def _is_blank(value: object) -> bool:
    return not isinstance(value, str) or not value.strip()


def _check_newbie_minimum(scenario: Scenario) -> None:
    """Newbie stories need a name, a one line idea and an opening to be playable."""
    if scenario.mode != NEWBIE_MODE:
        return
    legacy_opening = (scenario.world_data or {}).get(LEGACY_OPENING_PROMPT_KEY)
    missing = [
        label
        for label, is_missing in (
            ("name", _is_blank(scenario.title)),
            ("one line idea", _is_blank(scenario.logline)),
            (
                "opening",
                _is_blank(scenario.opening_scene) and _is_blank(legacy_opening),
            ),
        )
        if is_missing
    ]
    if missing:
        raise ScenarioValidationError(f"To publish, add: {', '.join(missing)}.")


def _check_strategy_document(scenario: Scenario) -> None:
    if scenario.mode != STRATEGY_MODE:
        return
    document = StrategyScenario.model_validate(scenario.strategy_document)
    report = check_publishable(document)
    if report.is_publishable:
        return
    messages = "; ".join(issue.message for issue in report.blocking)
    raise ScenarioValidationError(f"Strategy scenario cannot publish: {messages}")


def _check_content_tags(scenario: Scenario) -> None:
    """Re-validate thematic tags in case the vocabulary changed since they were saved."""
    try:
        validate_content_tags(list(scenario.content_tags))
    except ValueError as error:
        raise ScenarioValidationError(str(error)) from error


async def _check_map_start_pin(scenario: Scenario, map_repo: MapRepo) -> None:
    """A scenario with ≥1 map must have exactly one start-location pin.

    The DB's partial unique index already guarantees at most one; this adds
    the "at least one" business check the DB can't express, blocking publish
    with a clear error rather than shipping a scenario TRS can't seed a
    starting current_location_id for.
    """
    map_count = await map_repo.count_maps_by_scenario(scenario.scenario_id)
    if map_count == 0:
        return
    start_pin = await map_repo.get_start_pin_by_scenario(scenario.scenario_id)
    if start_pin is None:
        raise MapPublishValidationError()
