import httpx
from app.config import Settings
from app.integrations.llm_client import SpeechGradeAnswer, SpeechProviderClient
from app.models.speech_grading import SpeechBriefing
from app.models.world_player import PlayerRuler
from app.services.speech_briefing import build_mood_briefing, build_speech_briefing
from app.services.speech_grade_service import grade_briefing
from strategy_contracts.battle_speech import ExhaustionBucket, MoraleBucket
from strategy_contracts.scenario import AmbitionDefinition
from strategy_contracts.traits import TraitAxis, TraitDefinition
from tests.engine.battles.builders import battle_fixture

CUSTOM_TRAIT = TraitDefinition(
    id="gallows_humor",
    name="Gallows Humor",
    description="Laughs in the face of ruin",
    effects={TraitAxis.PRIDE: 1},
)


class FakeSpeechClient:
    def __init__(self, error: Exception | None = None) -> None:
        self._error = error
        self.briefings: list[SpeechBriefing] = []

    async def grade_speech(
        self, settings: Settings, briefing: SpeechBriefing
    ) -> SpeechGradeAnswer:
        self.briefings.append(briefing)
        if self._error is not None:
            raise self._error
        return SpeechGradeAnswer(
            addresses_fears=5, fits_ruler_character=5, promises_made=5
        )


def briefing_with_custom_trait() -> SpeechBriefing:
    world, scenario = battle_fixture()
    world.ruler = PlayerRuler(
        name="Valdren",
        epithet="The Unbowed",
        trait_ids=["honorable", "gallows_humor"],
        ambition_ids=["ambition_peace"],
    )
    scenario.custom_traits = [CUSTOM_TRAIT]
    scenario.ambitions = [
        AmbitionDefinition.model_construct(id="ambition_peace", name="Lasting Peace")
    ]
    return build_speech_briefing(world, scenario, "army_a", ["Hold fast!"])


def enabled() -> Settings:
    return Settings(speech_provider_enabled=True)


def test_briefing_resolves_builtin_and_custom_ruler_traits() -> None:
    briefing = briefing_with_custom_trait()
    joined = " ".join(briefing.ruler_trait_notes)
    assert "Gallows Humor: Laughs in the face of ruin" in joined
    assert len(briefing.ruler_trait_notes) == 2
    assert briefing.ruler_ambitions == ["Lasting Peace"]
    assert (briefing.ruler_epithet, briefing.troop_count) == ("The Unbowed", 1000)


async def test_a_provider_answer_becomes_a_bounded_outcome() -> None:
    client = FakeSpeechClient()
    outcome = await grade_briefing(briefing_with_custom_trait(), enabled(), client)
    assert outcome.morale_delta_percent == 15
    assert client.briefings[0].ruler_name == "Valdren"


async def test_a_disabled_provider_gives_a_neutral_outcome_without_calling() -> None:
    client = FakeSpeechClient()
    outcome = await grade_briefing(briefing_with_custom_trait(), Settings(), client)
    assert outcome.morale_delta_percent == 0
    assert client.briefings == []


def test_mood_briefing_carries_buckets_and_talks_but_no_raw_numbers() -> None:
    world, scenario = battle_fixture()
    world.armies["army_a"].morale = 25
    world.armies["army_a"].fatigue = 80
    briefing = build_mood_briefing(world, scenario, "army_a", ["First", "Second"])
    assert briefing.talks == ["First", "Second"]
    assert briefing.army_mood.morale == MoraleBucket.SHAKEN
    assert briefing.army_mood.exhaustion == ExhaustionBucket.SPENT
    assert "troop_count" not in briefing.model_dump()


async def test_injected_extra_fields_in_the_answer_fall_back_to_zero() -> None:
    injected = {
        "addresses_fears": 5,
        "fits_ruler_character": 5,
        "promises_made": 5,
        "morale_delta_percent": 99,
    }

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=injected)

    settings = Settings(
        speech_provider_enabled=True,
        speech_provider_url="https://provider.invalid/speech",
        speech_provider_api_key="test-only",
        speech_provider_model="fake-model",
    )
    client = SpeechProviderClient(httpx.MockTransport(handler))
    outcome = await grade_briefing(briefing_with_custom_trait(), settings, client)
    assert outcome.morale_delta_percent == 0


async def test_provider_failures_fall_back_to_a_neutral_outcome() -> None:
    for error in (httpx.ConnectError("down"), TimeoutError(), ValueError("bad")):
        client = FakeSpeechClient(error)
        outcome = await grade_briefing(briefing_with_custom_trait(), enabled(), client)
        assert (outcome.morale_delta_percent, outcome.rubric_scores) == (0, {})
