from app.engine.diplomacy.phase import TimePhase
from app.engine.hashing import world_hash
from app.models.world_diplomacy import PrisonerKind, PrisonerState
from app.models.world_events import EventLogEntry
from app.models.world_state import WorldState
from strategy_contracts.enums import TroopType

from tests.engine.diplomacy.builders import run_phase, set_traits
from tests.engine.peace.builders import PLAYER, WRATHFUL_RIVAL, make_world

HOLDER = WRATHFUL_RIVAL
TURNS = 12
CAPTIVES = (("prisoner_a", 60), ("prisoner_b", 30), ("prisoner_c", 90))


def _start(traits: list[str], peace_ruleset: int = 2) -> WorldState:
    world = make_world()
    world.peace_ruleset = peace_ruleset
    set_traits(world, HOLDER, traits)
    for prisoner_id, count in CAPTIVES:
        world.prisoners.append(
            PrisonerState(
                id=prisoner_id,
                held_by_id=HOLDER,
                origin_faction_id=PLAYER,
                kind=PrisonerKind.TROOPS,
                troop_count=count,
                origin_battle_id="battle_1",
                troops_by_type={TroopType.INFANTRY: count},
            )
        )
    return world


def _play(world: WorldState) -> tuple[list[str], list[EventLogEntry], WorldState]:
    hashes = [world_hash(world)]
    events: list[EventLogEntry] = []
    for _ in range(TURNS):
        world.clock.turn += 1
        result = run_phase(TimePhase(), world)
        world = result.world
        events += result.events
        hashes.append(world_hash(world))
    return hashes, events, world


def test_captivity_over_many_turns_replays_to_identical_hashes_and_events() -> None:
    first_hashes, first_events, _ = _play(_start(["cruel"]))
    second_hashes, second_events, _ = _play(_start(["cruel"]))

    assert first_hashes == second_hashes
    assert first_events == second_events


def test_the_drain_and_the_executions_actually_change_the_world() -> None:
    hashes, _, final = _play(_start(["cruel"]))

    assert len(set(hashes)) > 2
    assert final.prisoners == []
    assert (
        final.factions[PLAYER].stability != _start(["cruel"]).factions[PLAYER].stability
    )


def test_a_ruleset_one_world_is_untouched_by_the_captivity_steps() -> None:
    start = _start(["cruel"], peace_ruleset=1)

    _, _, final = _play(start.model_copy(deep=True))

    assert len(final.prisoners) == len(CAPTIVES)
    assert final.factions[PLAYER].stability == start.factions[PLAYER].stability


def test_captivity_state_survives_a_document_round_trip() -> None:
    _, _, final = _play(_start(["honorable"]))

    restored = WorldState.model_validate(final.model_dump(mode="json"))

    assert world_hash(restored) == world_hash(final)
