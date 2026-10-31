import itertools

from app.engine.hashing import world_hash
from app.engine.movement.costs import leg_cost
from app.engine.movement.map_index import build_map_index
from app.models.world_army import ArmyState
from app.models.world_clock import TurnClock
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from strategy_contracts.enums import RelationStatus, Terrain, TroopType
from strategy_contracts.scenario import MovementTuning

from tests.engine.movement.builders import (
    FACTION_A,
    FACTION_B,
    FACTION_C,
    halt_order,
    make_army,
    make_map,
    make_scenario,
    make_world_for,
    move_order,
    run_movement,
)

FACTIONS = [FACTION_A, FACTION_B, FACTION_C]
PAIRS = [(FACTION_A, FACTION_B), (FACTION_A, FACTION_C), (FACTION_B, FACTION_C)]
MAX_REGIONS = 7
MAX_ARMIES = 4
TURNS = 4
PROPERTY_SETTINGS = settings(
    max_examples=60,
    deadline=None,
    derandomize=True,
    suppress_health_check=[HealthCheck.too_slow],
)


@st.composite
def games(draw):
    count = draw(st.integers(min_value=3, max_value=MAX_REGIONS))
    names = [f"reg_{index}" for index in range(count)]
    terrains = {name: draw(st.sampled_from(list(Terrain))) for name in names}
    links = {(names[index], names[index + 1]) for index in range(count - 1)}
    extra = draw(
        st.sets(st.tuples(st.sampled_from(names), st.sampled_from(names)), max_size=4)
    )
    links |= {(left, right) for left, right in extra if left != right}
    roads = draw(st.sets(st.sampled_from(sorted(links)), max_size=count))
    owners = {name: draw(st.sampled_from([None, *FACTIONS])) for name in names}
    armies = []
    for index in range(draw(st.integers(min_value=1, max_value=MAX_ARMIES))):
        troops = {
            troop_type: draw(st.integers(min_value=0, max_value=4000))
            for troop_type in draw(
                st.sets(st.sampled_from(list(TroopType)), min_size=1)
            )
        }
        armies.append(
            make_army(
                f"army_{index}",
                draw(st.sampled_from(FACTIONS)),
                draw(st.sampled_from(names)),
                troops,
                draw(st.integers(min_value=0, max_value=100)),
            )
        )
    statuses = {pair: draw(st.sampled_from([*RelationStatus, None])) for pair in PAIRS}
    statuses = {pair: status for pair, status in statuses.items() if status}
    world = make_world_for(
        owners, armies, statuses, start_month=draw(st.integers(1, 12))
    )
    scenario = make_scenario(make_map(terrains, sorted(links), sorted(roads)))
    script = [
        [draw(order_for(names, armies)) for _ in range(draw(st.integers(1, 4)))]
        for _ in range(TURNS)
    ]
    return world, scenario, script


def order_for(names, armies):
    owners = {army.id: army.owner_id for army in armies}
    army_id = st.sampled_from(sorted(owners))
    region = st.sampled_from(names)
    # NOTE: weighted towards valid orders from the real owner so marches actually happen.
    mover = st.builds(
        lambda chosen, target: ("move", chosen, target, owners[chosen]), army_id, region
    )
    halter = st.builds(lambda chosen: ("halt", chosen, None, owners[chosen]), army_id)
    impostor = st.builds(
        lambda chosen, target, other: ("move", chosen, target, other),
        army_id,
        region,
        st.sampled_from(FACTIONS),
    )
    return st.one_of(mover, mover, mover, halter, impostor)


def _queued(script_turn, turn: int):
    queued = []
    for index, (kind, army_id, region, faction) in enumerate(script_turn):
        order_id = f"o{turn}_{index}"
        if kind == "move":
            queued.append(move_order(order_id, army_id, region, faction))
        else:
            queued.append(halt_order(order_id, army_id, faction))
    return queued


def _play(world, scenario, script):
    history = [world]
    for turn, script_turn in enumerate(script):
        result = run_movement(world, scenario, _queued(script_turn, turn))
        world = result.world
        world.clock.turn += 1
        history.append(world)
    return history


def _total_troops(world) -> dict[str, int]:
    return {
        army_id: sum(army.troops.values()) for army_id, army in world.armies.items()
    }


@PROPERTY_SETTINGS
@given(games())
def test_movement_never_creates_or_destroys_troops(game) -> None:
    world, scenario, script = game
    for state in _play(world, scenario, script):
        assert _total_troops(state) == _total_troops(world)


@PROPERTY_SETTINGS
@given(games())
def test_every_army_stands_in_one_valid_place_with_a_walkable_march(game) -> None:
    world, scenario, script = game
    index = build_map_index(scenario.map)
    for state in _play(world, scenario, script):
        for army in state.armies.values():
            assert army.location_id in index.terrain
            march = army.march
            if march is None:
                continue
            assert march.from_id == army.location_id
            assert march.to_id in index.neighbors[march.from_id]
            stops = [march.from_id, *march.route]
            if not march.is_returning:
                stops.insert(1, march.to_id)
            assert len(set(stops)) == len(stops)
            for left, right in itertools.pairwise(stops):
                assert right in index.neighbors[left]
            if march.is_returning:
                assert march.leg_progress > 0


@PROPERTY_SETTINGS
@given(games())
def test_an_active_march_never_holds_more_progress_than_its_leg_costs(game) -> None:
    world, scenario, script = game
    index = build_map_index(scenario.map)
    tuning = scenario.tuning.movement
    final = _play(world, scenario, script)[-1]
    clock = final.clock.model_copy(update={"turn": final.clock.turn - 1})
    for army in final.armies.values():
        march = army.march
        if march is None or march.is_halted or march.is_returning:
            continue
        cost = leg_cost(index, army, clock, tuning, march.from_id, march.to_id)
        assert march.leg_progress < cost.total


@PROPERTY_SETTINGS
@given(games())
def test_a_battle_never_lists_an_army_twice_or_on_both_sides(game) -> None:
    world, scenario, script = game
    for state in _play(world, scenario, script):
        for battle in state.pending_battles:
            sides = battle.attacker_army_ids + battle.defender_army_ids
            assert len(sides) == len(set(sides))
            assert battle.attacker_army_ids == sorted(battle.attacker_army_ids)
            assert battle.defender_army_ids == sorted(battle.defender_army_ids)
            for army_id in sides:
                assert state.armies[army_id].march is None


@PROPERTY_SETTINGS
@given(games(), st.randoms(use_true_random=False))
def test_input_order_and_dict_order_do_not_change_the_result(game, shuffler) -> None:
    world, scenario, script = game
    orders = _queued(script[0], 0)
    reference = run_movement(world, scenario, orders).world
    shuffled_orders = list(orders)
    shuffler.shuffle(shuffled_orders)
    reordered = world.model_copy(deep=True)
    armies = list(reordered.armies.items())
    shuffler.shuffle(armies)
    reordered.armies = dict(armies)
    result = run_movement(reordered, scenario, shuffled_orders).world
    assert world_hash(result) == world_hash(reference)


@PROPERTY_SETTINGS
@given(games())
def test_running_the_same_turn_twice_gives_the_same_world(game) -> None:
    world, scenario, script = game
    orders = _queued(script[0], 0)
    first = run_movement(world, scenario, orders)
    second = run_movement(world, scenario, orders)
    assert world_hash(first.world) == world_hash(second.world)
    assert first.events == second.events


@PROPERTY_SETTINGS
@given(games())
def test_the_phase_leaves_the_world_it_was_given_untouched(game) -> None:
    world, scenario, script = game
    snapshot = world.model_dump()
    run_movement(world, scenario, _queued(script[0], 0))
    assert world.model_dump() == snapshot


def _plain_cost(**changes) -> int:
    fields = {
        "troops": {TroopType.INFANTRY: 500},
        "morale": 70,
        "start_month": 6,
        "has_road": False,
        "terrain": Terrain.PLAIN,
    }
    fields.update(changes)
    roads = [("reg_a", "reg_b")] if fields["has_road"] else []
    index = build_map_index(
        make_map(
            {"reg_a": Terrain.PLAIN, "reg_b": fields["terrain"]},
            [("reg_a", "reg_b")],
            roads,
        )
    )
    army: ArmyState = make_army(
        "army_a", FACTION_A, "reg_a", fields["troops"], fields["morale"]
    )
    clock = TurnClock(turn=0, start_year=1000, start_month=fields["start_month"])
    return leg_cost(index, army, clock, MovementTuning(), "reg_a", "reg_b").total


@PROPERTY_SETTINGS
@given(
    terrain=st.sampled_from(list(Terrain)),
    troops=st.integers(1, 20000),
    extra=st.integers(0, 20000),
    morale=st.integers(0, 100),
    lower=st.integers(0, 100),
    month=st.integers(1, 12),
)
def test_costs_are_monotone_in_every_factor(
    terrain, troops, extra, morale, lower, month
):
    base = _plain_cost(terrain=terrain, troops={TroopType.INFANTRY: troops})
    bigger = _plain_cost(terrain=terrain, troops={TroopType.INFANTRY: troops + extra})
    assert bigger >= base
    steady = _plain_cost(terrain=terrain, morale=max(morale, lower))
    shaken = _plain_cost(terrain=terrain, morale=min(morale, lower))
    assert shaken >= steady
    assert _plain_cost(terrain=terrain, has_road=True) <= _plain_cost(terrain=terrain)
    assert _plain_cost(terrain=terrain, start_month=month) >= _plain_cost(
        terrain=terrain, start_month=6
    )
