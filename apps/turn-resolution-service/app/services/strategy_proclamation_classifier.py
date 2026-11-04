import json
from uuid import UUID

from app.exceptions.turn_exceptions import LlmUnavailableError
from app.integrations import openai_compatible_client
from app.services.proclamation_classifier_prompt import (
    build_classifier_system_prompt,
    build_classifier_user_prompt,
)
from app.services.rate_limit.policies import QuotaFeature
from app.services.rate_limit.quota_service import QuotaService
from strategy_contracts.proclamation import (
    EstatePillar,
    ProclamationBurden,
    ProclamationDomain,
    ProclamationDraft,
)


def _heuristic_classify(text: str) -> ProclamationDraft:
    lowered = text.lower()
    if any(
        k in lowered
        for k in ("tax", "gold", "silver", "tariff", "coin", "treasury", "merchant")
    ):
        return ProclamationDraft(
            is_recognized=True,
            domain=ProclamationDomain.EMERGENCY_TAXATION,
            burden=ProclamationBurden.MODERATE,
            target_estate=EstatePillar.BURGHERS,
            legal_summary=text[:200],
        )
    if any(
        k in lowered
        for k in (
            "conscript",
            "soldier",
            "archer",
            "army",
            "troop",
            "bannermen",
            "martial",
        )
    ):
        return ProclamationDraft(
            is_recognized=True,
            domain=ProclamationDomain.MARTIAL_LEVIES,
            burden=ProclamationBurden.MODERATE,
            target_estate=EstatePillar.MILITARY,
            legal_summary=text[:200],
        )
    if any(k in lowered for k in ("church", "faith", "tithe", "heresy", "god")):
        return ProclamationDraft(
            is_recognized=True,
            domain=ProclamationDomain.RELIGIOUS_ORTHODOXY,
            burden=ProclamationBurden.MODERATE,
            target_estate=EstatePillar.CLERGY,
            legal_summary=text[:200],
        )
    if any(k in lowered for k in ("lord", "baron", "charter", "privilege", "noble")):
        return ProclamationDraft(
            is_recognized=True,
            domain=ProclamationDomain.NOBLE_PRIVILEGES,
            burden=ProclamationBurden.MODERATE,
            target_estate=EstatePillar.NOBILITY,
            legal_summary=text[:200],
        )
    if any(k in lowered for k in ("grain", "bread", "relief", "peasant", "famine")):
        return ProclamationDraft(
            is_recognized=True,
            domain=ProclamationDomain.POPULAR_RELIEF,
            burden=ProclamationBurden.MODERATE,
            target_estate=EstatePillar.BURGHERS,
            legal_summary=text[:200],
        )
    return ProclamationDraft(
        is_recognized=False,
        fallback_reason="unintelligible",
        legal_summary="Unrecognized decree text.",
    )


async def classify_sovereign_proclamation(
    text: str, user_id: UUID, quota: QuotaService
) -> ProclamationDraft:
    reservation = await quota.reserve(QuotaFeature.STRATEGY_PROCLAMATION, user_id)
    system_prompt = build_classifier_system_prompt()
    user_prompt = build_classifier_user_prompt(text)
    try:
        raw_json = await openai_compatible_client.chat_completion(
            system_prompt=system_prompt,
            user_message=user_prompt,
            response_format={"type": "json_object"},
        )
        parsed = json.loads(raw_json)
        return ProclamationDraft.model_validate(parsed)
    except (LlmUnavailableError, json.JSONDecodeError, ValueError, RuntimeError):
        if reservation is not None:
            await reservation.refund()
        return _heuristic_classify(text)
