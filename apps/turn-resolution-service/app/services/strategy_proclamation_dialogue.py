import json
from collections.abc import AsyncIterator
from uuid import UUID

from app.config import settings
from app.exceptions.turn_exceptions import LlmUnavailableError
from app.integrations import openai_compatible_client
from app.services.proclamation_dialogue_prompt import (
    build_minister_dialogue_system_prompt,
    build_minister_dialogue_user_prompt,
)
from app.services.rate_limit.policies import QuotaFeature
from app.services.rate_limit.quota_service import QuotaService
from strategy_contracts.proclamation import (
    ProclamationBurden,
    ProclamationDomain,
    ProclamationDraft,
)


def _get_fallback_dialogue(
    domain: ProclamationDomain, _burden: ProclamationBurden
) -> list[str]:
    return [
        "[CHANCELLOR]: The ancient charters must not be trampled lightly, Sire.",
        "[MARSHAL]: Our borders demand discipline, steel, and ready rations.",
        "[TREASURER]: Every coin diverted from trade weakens the realm's merchants.",
        "[PRELATE]: May the heavens guide your decree with wisdom and restraint.",
    ]


async def stream_proclamation_dialogue(
    draft: ProclamationDraft,
    turn_context: dict[str, object] | None = None,
    player_speech: str | None = None,
) -> AsyncIterator[dict[str, str]]:
    sys = build_minister_dialogue_system_prompt()
    usr = build_minister_dialogue_user_prompt(draft, turn_context, player_speech)
    try:
        async for chunk in openai_compatible_client.stream_narration(
            system_instruction=sys,
            prompt=usr,
            timeout_seconds=settings.narration_timeout_seconds,
        ):
            yield {"event": "narration", "data": chunk}
    except (LlmUnavailableError, RuntimeError, TimeoutError):
        for line in _get_fallback_dialogue(draft.domain, draft.burden):
            yield {"event": "narration", "data": line + "\n"}
    yield {"event": "done", "data": json.dumps({"status": "completed"})}


async def open_proclamation_dialogue(
    draft: ProclamationDraft,
    turn_context: dict[str, object],
    player_speech: str | None,
    user_id: UUID,
    quota: QuotaService,
) -> AsyncIterator[dict[str, str]]:
    await quota.reserve(QuotaFeature.STRATEGY_PROCLAMATION, user_id)
    return stream_proclamation_dialogue(draft, turn_context, player_speech)
