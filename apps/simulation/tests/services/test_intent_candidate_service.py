from app.config import Settings
from app.engine.battles.policy import select_intent
from app.engine.battles.views import intent_briefing
from app.models.battle_intelligence import IntentKind, IntentSource
from app.models.battle_progress import IntentRequest
from app.models.intent_briefing import IntentBriefing
from app.services.intent_candidate_service import create_candidate
from tests.engine.battles.builders import DEFENDER, battle_fixture, start_battle


class FakeIntentClient:
    async def generate_intent(
        self, settings: Settings, briefing: IntentBriefing
    ) -> IntentKind:
        return IntentKind.PRESS


def intent_request() -> IntentRequest:
    world, scenario = battle_fixture()
    start_battle(world, scenario)
    briefing = intent_briefing(world, world.battles[0].id, DEFENDER, scenario)
    fallback = select_intent(briefing, scenario.tuning.battle)
    return IntentRequest(
        playthrough_id=world.playthrough_id,
        request_id="intent:fixed",
        battle_id=fallback.battle_id,
        faction_id=fallback.faction_id,
        campaign_turn=fallback.campaign_turn,
        intended_wave=fallback.intended_wave,
        input_hash=fallback.input_hash,
        observation_fingerprint=fallback.observation_fingerprint,
        policy_version=fallback.policy_version,
        redacted_input=briefing,
        fallback=fallback,
    )


async def test_candidate_copies_frozen_identity_and_validates_menu_choice() -> None:
    request = intent_request()
    candidate = await create_candidate(request, Settings(), FakeIntentClient())

    assert candidate.source == IntentSource.MODEL
    assert candidate.kind == IntentKind.PRESS
    assert candidate.id == request.fallback.id
    assert candidate.request_id == request.request_id
    assert candidate.input_hash == request.input_hash
