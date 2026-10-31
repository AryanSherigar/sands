from app.engine.stances.apply import apply_due_stances
from app.models.stance import StanceChoice, StanceSource
from app.models.world_character import LeaderState
from app.models.world_faction import StanceState
from app.models.world_state import WorldState

from tests.models.builders import make_world

AI_FACTION = "house_ashford"


def _world(turn: int = 3) -> WorldState:
    world = make_world()
    world.clock.turn = turn
    world.leaders = {
        "mira": LeaderState(id="mira", name="Mira", faction_id=AI_FACTION, age=40),
    }
    world.factions[AI_FACTION].leader_id = "mira"
    return world


def _choice(due_turn: int, leader_id: str = "mira", option_id: str = "expand"):
    return StanceChoice(
        leader_id=leader_id,
        faction_id=AI_FACTION,
        due_turn=due_turn,
        option_id=option_id,
        source=StanceSource.MODEL,
        reason_code="model_pick",
        input_hash="hash-1",
    )


def test_choice_applies_only_on_its_due_turn() -> None:
    world = _world(turn=3)
    apply_due_stances(world, {"mira": _choice(due_turn=4)})
    assert world.factions[AI_FACTION].stance == StanceState()
    apply_due_stances(world, {"mira": _choice(due_turn=3)})
    assert world.factions[AI_FACTION].stance == StanceState(
        option_id="expand", chosen_turn=3, requested_for_turn=None
    )


def test_unknown_leader_choice_is_ignored() -> None:
    world = _world()
    apply_due_stances(world, {"ghost": _choice(3, leader_id="ghost")})
    assert world.factions[AI_FACTION].stance == StanceState()


def test_choice_for_a_replaced_leader_is_ignored() -> None:
    world = _world()
    world.leaders["heir"] = LeaderState(
        id="heir", name="Heir", faction_id=AI_FACTION, age=20
    )
    world.factions[AI_FACTION].leader_id = "heir"
    apply_due_stances(world, {"mira": _choice(3)})
    assert world.factions[AI_FACTION].stance == StanceState()


def test_no_recorded_choice_keeps_previous_stance() -> None:
    world = _world()
    world.factions[AI_FACTION].stance = StanceState(option_id="turtle", chosen_turn=1)
    apply_due_stances(world, {})
    assert world.factions[AI_FACTION].stance.option_id == "turtle"


def test_application_order_does_not_depend_on_mapping_order() -> None:
    first = _world()
    second = _world()
    first.leaders["other"] = LeaderState(
        id="other", name="Other", faction_id="house_carrow", age=30
    )
    second.leaders["other"] = first.leaders["other"].model_copy()
    for world in (first, second):
        world.factions["house_carrow"].leader_id = "other"
    mira, other = (
        _choice(3),
        _choice(3, "other", "turtle").model_copy(update={"faction_id": "house_carrow"}),
    )
    apply_due_stances(first, {"mira": mira, "other": other})
    apply_due_stances(second, {"other": other, "mira": mira})
    assert first == second
