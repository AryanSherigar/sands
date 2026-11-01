from app.config import Settings
from app.integrations.llm_client import StanceAnswer
from app.models.stance import (
    StanceBriefing,
    StanceChoice,
    StanceMenuItem,
    StanceRequest,
    StanceSource,
)
from app.models.world_character import LeaderState
from app.models.world_state import WorldState
from strategy_contracts.scenario import StrategyScenario
from tests.models.builders import PLAYTHROUGH_ID, make_world

AI_FACTION = "house_ashford"
LEADER_ID = "mira"
MENU_IDS = ["expand", "turtle"]
PRIVATE_DESCRIPTION = "secret-scenario-lore-about-the-marches"


def ready_settings(**overrides: object) -> Settings:
    return Settings(
        stance_provider_enabled=True,
        stance_provider_url="https://provider.invalid/stance",
        stance_provider_api_key="test-only",
        stance_provider_model="fake-model",
        **overrides,
    )


def world_with_ai_leader() -> WorldState:
    world = make_world()
    world.leaders = {
        LEADER_ID: LeaderState(
            id=LEADER_ID, name="Mira", faction_id=AI_FACTION, age=40
        ),
    }
    world.factions[AI_FACTION].leader_id = LEADER_ID
    return world


def single_stance_scenario() -> StrategyScenario:
    return StrategyScenario.model_validate(
        {
            "factions": [
                {
                    "id": AI_FACTION,
                    "name": "Ashford",
                    "color": "#aabbcc",
                    "stance_ids": ["turtle"],
                }
            ]
        }
    )


def fallback_choice(due_turn: int = 1) -> StanceChoice:
    return StanceChoice(
        leader_id=LEADER_ID,
        faction_id=AI_FACTION,
        due_turn=due_turn,
        option_id="turtle",
        source=StanceSource.FALLBACK,
        reason_code="fallback_default",
        input_hash="hash-1",
    )


def stance_request(due_turn: int = 1) -> StanceRequest:
    return StanceRequest(
        playthrough_id=PLAYTHROUGH_ID,
        request_id=f"stance:{LEADER_ID}:{due_turn}",
        leader_id=LEADER_ID,
        faction_id=AI_FACTION,
        due_turn=due_turn,
        input_hash="hash-1",
        briefing=StanceBriefing(
            leader_name="Mira",
            trait_notes=[],
            ambitions=[],
            memories=[],
            opinions=[],
            current_option_id=None,
            menu=[
                StanceMenuItem(
                    id=stance_id,
                    name=stance_id.title(),
                    description=PRIVATE_DESCRIPTION,
                )
                for stance_id in MENU_IDS
            ],
        ),
        fallback=fallback_choice(due_turn),
    )


class FakeStanceClient:
    def __init__(self, answer: str | None = None, error: Exception | None = None):
        self._answer = answer
        self._error = error
        self.calls = 0

    async def pick_stance(
        self, settings: Settings, briefing: StanceBriefing
    ) -> StanceAnswer:
        self.calls += 1
        if self._error is not None:
            raise self._error
        return StanceAnswer(option_id=self._answer or "")
