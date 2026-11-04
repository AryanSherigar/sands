"""Drafts a coronation chronicle entry for a customized strategy ruler."""

from app.config import settings
from app.db.models.scenario import Scenario
from app.db.models.user import User
from app.exceptions.scenario_exceptions import (
    ScenarioAccessDeniedError,
    ScenarioNotFoundError,
)
from app.integrations import text_gen_client
from app.models.strategy_ruler import RulerBackstoryRequest
from app.repositories.scenario_repo import ScenarioRepo
from app.services.rate_limit.policies import QuotaFeature
from app.services.rate_limit.quota_service import QuotaService, quota_scope

BACKSTORY_MAX_OUTPUT_TOKENS = 180
_DEFAULT_TRAIT = "steadfast"
_DEFAULT_AMBITION = "prosperity"
_MODE_STRATEGY = "strategy"
_STATUS_PUBLISHED = "published"
_STATUS_ARCHIVED = "archived"


def build_backstory_prompt(req: RulerBackstoryRequest) -> str:
    traits = ", ".join(req.trait_ids) or _DEFAULT_TRAIT
    ambitions = ", ".join(req.ambition_ids) or _DEFAULT_AMBITION
    epithet_part = f", {req.epithet}" if req.epithet else ""
    return (
        "You are a medieval court chronicler. Write a concise 2-3 sentence evocative "
        f"coronation chronicle entry for {req.ruler_name}{epithet_part} of {req.faction_id}. "
        f"Incorporate their virtues: {traits} and ambition: {ambitions}. "
        "Style: ancient, atmospheric, poetic parchment tone without modern clichés."
    )


async def generate_ruler_backstory(req: RulerBackstoryRequest) -> str:
    """Generate 2-3 sentences of atmospheric coronation chronicle prose."""
    return await text_gen_client.generate_text(
        build_backstory_prompt(req),
        BACKSTORY_MAX_OUTPUT_TOKENS,
        settings.text_generation_timeout_seconds,
    )


def _ensure_can_draft_for(scenario: Scenario | None, user: User) -> None:
    if (
        scenario is None
        or scenario.mode != _MODE_STRATEGY
        or scenario.status == _STATUS_ARCHIVED
    ):
        raise ScenarioNotFoundError()
    is_owner = scenario.creator_id == user.user_id
    if not is_owner and scenario.status != _STATUS_PUBLISHED:
        raise ScenarioAccessDeniedError()


async def draft_ruler_backstory(
    req: RulerBackstoryRequest,
    user: User,
    scenario_repo: ScenarioRepo,
    quota_service: QuotaService | None,
) -> str:
    """Draft a backstory for the scenario's owner, or any player of a published one."""
    scenario = await scenario_repo.get_by_id(req.scenario_id)
    _ensure_can_draft_for(scenario, user)
    async with quota_scope(quota_service, QuotaFeature.RULER_BACKSTORY, user):
        return await generate_ruler_backstory(req)
