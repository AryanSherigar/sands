from app.models.world_diplomacy import AgentState, EnvoyState
from app.models.world_pressure import RumorState
from app.services.dispatch_materialization import build_dispatch_briefings
from strategy_contracts.agents import AgentTrait
from strategy_contracts.pressure import PressureBand, RumorTopic
from tests.engine.pressure.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    WRATHFUL_RIVAL,
    make_world,
)

BRIBER = CAUTIOUS_RIVAL


def _agent() -> AgentState:
    return AgentState(
        name="Aldous", traits=[AgentTrait.PIOUS], loyalty=61, bribed_by=BRIBER
    )


def _rumor(rumor_id: str, observer: str = PLAYER, envoy: str = "envoy_1"):
    return RumorState(
        id=rumor_id,
        observer_id=observer,
        about_faction_id=WRATHFUL_RIVAL,
        envoy_id=envoy,
        topic=RumorTopic.WILL,
        band=PressureBand.LOW,
        line_key="will.low",
        turn=3,
        is_hint_wrong=True,
    )


def _world(agent: AgentState | None = None, observer: str = PLAYER):
    world = make_world()
    world.envoys.append(
        EnvoyState(
            id="envoy_1",
            from_faction_id=observer,
            at_faction_id=WRATHFUL_RIVAL,
            agent=agent,
        )
    )
    world.pressure.rumors.append(_rumor("rumor_1", observer))
    return world


def test_new_rumor_with_agent_creates_one_briefing() -> None:
    briefings = build_dispatch_briefings(_world(_agent()), make_world())

    assert [b.rumor_id for b in briefings] == ["rumor_1"]
    assert briefings[0].reported_band is PressureBand.LOW
    assert briefings[0].agent.name == "Aldous"


def test_ai_observer_rumors_create_no_briefing() -> None:
    world = _world(_agent(), observer=CAUTIOUS_RIVAL)

    assert build_dispatch_briefings(world, make_world()) == []


def test_rumor_without_agent_creates_no_briefing() -> None:
    assert build_dispatch_briefings(_world(None), make_world()) == []


def test_rumor_already_in_previous_world_is_not_repeated() -> None:
    world = _world(_agent())

    assert build_dispatch_briefings(world, world) == []


def test_briefing_json_hides_truth_bribery_and_loyalty() -> None:
    dumped = build_dispatch_briefings(_world(_agent()), make_world())[0].model_dump(
        mode="json"
    )

    text = str(dumped)
    for secret in ("bribed", "is_hint_wrong", "loyalty", BRIBER, "true_band"):
        assert secret not in text
