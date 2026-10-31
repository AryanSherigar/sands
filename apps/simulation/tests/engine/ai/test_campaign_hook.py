from app.engine.ai.planner import plan_ai_orders
from app.engine.campaign import begin_campaign
from app.engine.commands.application import accept_command
from app.engine.commands.check import check_command
from app.engine.hashing import world_hash
from app.engine.replay import replay_history
from app.models.battle_progress import OperationGuard
from app.models.orders import SetTaxRateOrder
from app.models.replay import BeginCampaignReplayInput, ReplayStep, ReplayStepKind
from app.models.world_state import WorldState
from strategy_contracts.enums import TaxRate

from tests.engine.diplomacy.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    PLAYTHROUGH_ID,
    SCENARIO,
    make_world,
)


def _turtle_world(ai_ruleset: int = 1) -> WorldState:
    world = make_world()
    world.ai_ruleset = ai_ruleset
    world.factions[CAUTIOUS_RIVAL].stance.option_id = "turtle"
    return world


def _npc_commands(world: WorldState):
    return [
        item for item in world.accepted_commands if item.actor_id.startswith("npc:")
    ]


def _planned_commands(world: WorldState) -> list[str]:
    plan = plan_ai_orders(world, SCENARIO)
    return [item.command.model_dump_json() for item in _npc_commands(plan.world)]


def test_begin_with_ruleset_queues_and_applies_ai_orders() -> None:
    result = begin_campaign(_turtle_world(), SCENARIO)

    assert result.world.factions[CAUTIOUS_RIVAL].tax_rate == TaxRate.HIGH
    npc = _npc_commands(result.world)
    assert CAUTIOUS_RIVAL in {item.faction_id for item in npc}
    assert PLAYER not in {item.faction_id for item in npc}
    assert "ai_order_planned" in [event.kind for event in result.events]


def test_begin_without_ruleset_is_unchanged() -> None:
    result = begin_campaign(_turtle_world(ai_ruleset=0), SCENARIO)

    assert _npc_commands(result.world) == []
    assert result.world.factions[CAUTIOUS_RIVAL].tax_rate == TaxRate.NORMAL
    assert "ai_order_planned" not in [event.kind for event in result.events]


def test_player_queued_commands_do_not_change_ai_orders() -> None:
    world = _turtle_world()
    alone = _planned_commands(world)
    queued = accept_command(
        world,
        SCENARIO,
        SetTaxRateOrder(faction_id=PLAYER, tax_rate=TaxRate.LOW),
        command_id="player-1",
        operation_id="player-1",
        actor_id="player",
        faction_id=PLAYER,
        expected_turn=world.clock.turn,
        expected_wave=0,
    ).world

    assert _planned_commands(queued) == alone


def test_planning_ignores_other_factions_private_state() -> None:
    world = _turtle_world()
    baseline = _planned_commands(world)
    world.factions[PLAYER].treasury += 5000
    world.factions[PLAYER].stability = 5
    world.factions[PLAYER].intel = {}

    assert _planned_commands(world) == baseline


def test_ai_orders_pass_the_player_validators() -> None:
    before = _turtle_world()
    plan = plan_ai_orders(before, SCENARIO)

    for item in _npc_commands(plan.world):
        check = check_command(
            before,
            SCENARIO,
            item.command,
            faction_id=item.faction_id,
            expected_turn=before.clock.turn,
            expected_wave=0,
        )
        assert check.flag is None
        assert item.reserved_cost <= before.factions[item.faction_id].orders_remaining


def _begin_step(before: WorldState, after: WorldState) -> ReplayStep:
    guard = OperationGuard(
        operation_id="begin", expected_world_version=1, expected_turn=0, expected_wave=0
    )
    return ReplayStep(
        playthrough_id=PLAYTHROUGH_ID,
        sequence=1,
        operation_id="begin",
        kind=ReplayStepKind.BEGIN_CAMPAIGN,
        input=BeginCampaignReplayInput(guard=guard, stances=[]),
        before_hash=world_hash(before),
        after_hash=world_hash(after),
        turn=0,
        wave=0,
    )


def test_replay_reproduces_the_ai_planned_turn() -> None:
    before = _turtle_world()
    after = begin_campaign(before.model_copy(deep=True), SCENARIO).world

    replayed = replay_history(before, SCENARIO, [_begin_step(before, after)])

    assert replayed.world_hash == world_hash(after)
