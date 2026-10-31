from uuid import UUID

from app.engine.commands.application import accept_command
from app.engine.phases import Phase, PhaseContext, PhaseResult
from app.engine.rng import derive_rng
from app.engine.world_init import new_world
from app.models.orders import Order
from app.models.world_diplomacy import DiplomaticPlayState
from app.models.world_player import PlayerRuler
from app.models.world_state import CounterKind, WorldState
from strategy_contracts.examples import load_three_crowns_expanded
from strategy_contracts.scenario import StrategyScenario, Tuning

PLAYTHROUGH_ID = UUID("88888888-8888-8888-8888-888888888888")
SEED = 20261027
PLAYER = "house_ashford"
CAUTIOUS_RIVAL = "house_carrow"
WRATHFUL_RIVAL = "house_dunwick"
SCENARIO: StrategyScenario = load_three_crowns_expanded()
SCENARIO.tuning.order_costs = Tuning().order_costs


def make_world(player_faction_id: str = PLAYER) -> WorldState:
    ruler = PlayerRuler(
        name="Valdren",
        trait_ids=["honorable", "cautious"],
        ambition_ids=["ambition_peace"],
    )
    world = new_world(SCENARIO, PLAYTHROUGH_ID, SEED, player_faction_id, ruler)
    world.grounds = []
    world.counters.pop(CounterKind.GROUND, None)
    return world


def set_traits(world: WorldState, faction_id: str, trait_ids: list[str]) -> str:
    leader_id = world.factions[faction_id].leader_id
    assert leader_id is not None
    world.leaders[leader_id].trait_ids = trait_ids
    return leader_id


def queue_npc_order(
    world: WorldState, scenario: StrategyScenario, order: Order
) -> WorldState:
    target = getattr(order, "target_faction_id", "")
    identity = (
        f"npc:{order.faction_id}:{order.kind}:{target}:{len(world.accepted_commands)}"
    )
    return accept_command(
        world,
        scenario,
        order,
        command_id=identity,
        operation_id=identity,
        actor_id=f"npc:{order.faction_id}",
        faction_id=order.faction_id,
        expected_turn=world.clock.turn,
        expected_wave=0,
    ).world


def run_phase(phase: Phase, world: WorldState) -> PhaseResult:
    context = PhaseContext(
        scenario=SCENARIO,
        orders=(),
        rng=derive_rng(world.rng.seed, world.clock.turn, phase.name.value),
        resolved_outcomes={},
        recorded_answers={},
    )
    return phase.run(world.model_copy(deep=True), context)


def add_warning(world: WorldState, attacker_id: str, defender_id: str) -> None:
    world.plays.append(
        DiplomaticPlayState(
            id=f"play_warning_{len(world.plays)}",
            attacker_id=attacker_id,
            defender_id=defender_id,
            stage="resolved",
            kind="talks",
            due_turn=world.clock.turn,
        )
    )
