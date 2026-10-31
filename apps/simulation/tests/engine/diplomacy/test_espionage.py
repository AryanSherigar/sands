import pytest
from app.engine.diplomacy.phase import DiplomacyPhase
from app.engine.pressure.agents import bribe_price
from app.exceptions.command_exceptions import CommandError
from app.models.battle_command import Command
from app.models.orders import BribeEnvoyOrder
from app.models.world_diplomacy import AgentState, EnvoyState
from pydantic import TypeAdapter
from strategy_contracts.agents import AgentTrait

from tests.engine.diplomacy.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    make_world,
    queue_npc_order,
    run_phase,
)

LOYALTY = 50
RICH = 5000


@pytest.fixture(autouse=True)
def _agents_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(SCENARIO.tuning.agents, "is_enabled", True)


def _world(*, traits=(AgentTrait.HONEST,), bribed_by=None, treasury=RICH):
    world = make_world()
    world.envoys.append(
        EnvoyState(
            id="envoy_1",
            from_faction_id=PLAYER,
            at_faction_id=WRATHFUL_RIVAL,
            agent=AgentState(
                name="Aldous",
                traits=list(traits),
                loyalty=LOYALTY,
                bribed_by=bribed_by,
            ),
        )
    )
    world.factions[WRATHFUL_RIVAL].treasury = treasury
    return world


def _order(envoy_id: str = "envoy_1", briber: str = WRATHFUL_RIVAL) -> BribeEnvoyOrder:
    return BribeEnvoyOrder(faction_id=briber, envoy_id=envoy_id)


def _code(world, order) -> str:
    with pytest.raises(CommandError) as raised:
        queue_npc_order(world, SCENARIO, order)
    return raised.value.code


def test_bribe_sets_bribed_by_and_deducts_exact_price() -> None:
    world = _world()
    price = bribe_price(world.envoys[0].agent, SCENARIO.tuning.agents)
    queued = queue_npc_order(world, SCENARIO, _order())

    result = run_phase(DiplomacyPhase(), queued)

    assert result.world.envoys[0].agent.bribed_by == WRATHFUL_RIVAL
    assert result.world.factions[WRATHFUL_RIVAL].treasury == RICH - price
    assert [event.kind for event in result.events] == ["envoy_bribed"]


def test_bribe_event_subject_is_only_the_briber() -> None:
    result = run_phase(DiplomacyPhase(), queue_npc_order(_world(), SCENARIO, _order()))

    assert result.events[0].cause.subject_ids == [WRATHFUL_RIVAL]


def test_bribe_price_lower_for_incompetent_agent() -> None:
    plain = AgentState(name="A", traits=[AgentTrait.HONEST], loyalty=LOYALTY)
    clumsy = AgentState(name="B", traits=[AgentTrait.INCOMPETENT], loyalty=LOYALTY)
    tuning = SCENARIO.tuning.agents

    assert bribe_price(plain, tuning) == 140
    assert bribe_price(clumsy, tuning) == 98


def test_unknown_envoy_is_rejected() -> None:
    assert _code(_world(), _order("envoy_9")) == "unknown_envoy"


def test_envoy_in_another_court_is_rejected() -> None:
    assert _code(_world(), _order(briber=CAUTIOUS_RIVAL)) == "envoy_not_in_your_court"


def test_own_envoy_is_rejected() -> None:
    assert _code(_world(), _order(briber=PLAYER)) == "own_envoy"


def test_already_bribed_agent_is_rejected() -> None:
    world = _world(bribed_by=CAUTIOUS_RIVAL)

    assert _code(world, _order()) == "already_bribed"


def test_unaffordable_bribe_is_rejected() -> None:
    assert _code(_world(treasury=10), _order()) == "cannot_afford_bribe"


def test_agentless_envoy_is_rejected() -> None:
    world = _world()
    world.envoys[0].agent = None

    assert _code(world, _order()) == "no_agent"


def test_bribe_is_rejected_when_agents_are_disabled(monkeypatch) -> None:
    monkeypatch.setattr(SCENARIO.tuning.agents, "is_enabled", False)

    assert _code(_world(), _order()) == "agents_disabled"


def test_bribe_order_roundtrips_through_command_union() -> None:
    adapter = TypeAdapter(Command)
    order = _order()

    restored = adapter.validate_python(order.model_dump(mode="json"))

    assert restored == order
