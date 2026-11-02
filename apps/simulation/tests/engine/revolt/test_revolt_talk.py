import pytest
from app.engine.commands.application import accept_command
from app.engine.hashing import world_hash
from app.engine.internal.queued_responses import apply_queued_responses
from app.engine.revolt.arming import arm_revolt_talk, revolt_scene_id
from app.engine.revolt.closing import close_revolt_talk
from app.engine.revolt.watch import scan_covenants
from app.exceptions.command_exceptions import CampaignProgressError, CommandError
from app.models.battle_command import ResolveUprisingCommand
from app.models.world_events import PhaseName
from app.models.world_internal import UprisingResponse, UprisingState
from strategy_contracts.enums import TaxRate
from strategy_contracts.revolt import CovenantKind, CovenantStatus, RevoltTalkTuning
from strategy_contracts.scenario import StrategyScenario, Tuning
from strategy_contracts.scene import ChoiceOutcome

from tests.engine.economy.builders import (
    HOME,
    PLAYER,
    make_faction,
    make_region,
    make_world,
)
from tests.models.builders import PLAYTHROUGH_ID

UPRISING_ID = "uprising_home_0"
GOLD = 500


def _scenario(is_enabled: bool = True) -> StrategyScenario:
    return StrategyScenario(
        tuning=Tuning(revolt_talk=RevoltTalkTuning(is_enabled=is_enabled))
    )


def _world():
    faction = make_faction(PLAYER)
    faction.treasury = GOLD
    world = make_world(
        regions=[make_region(HOME, PLAYER, unrest=80)], factions=[faction]
    )
    world.playthrough_id = PLAYTHROUGH_ID
    world.internal_ruleset = 1
    world.uprisings = [
        UprisingState(
            id=UPRISING_ID,
            region_id=HOME,
            faction_id=PLAYER,
            started_turn=0,
            trigger_unrest=80,
            income_penalty_percent=10,
            manpower_penalty_percent=10,
            supply_penalty_percent=10,
        )
    ]
    return world


def _negotiate(world, scenario, command_id: str = "talk"):
    return accept_command(
        world,
        scenario,
        ResolveUprisingCommand(
            faction_id=PLAYER,
            uprising_id=UPRISING_ID,
            response=UprisingResponse.NEGOTIATE,
        ),
        command_id=command_id,
        operation_id=command_id,
        actor_id="owner",
        faction_id=PLAYER,
        expected_turn=0,
        expected_wave=0,
    )


def _armed_world(scenario):
    world = _negotiate(_world(), scenario).world
    arm_revolt_talk(world, scenario)
    return world, world.progress.pending_scene_id


def test_negotiate_queues_a_talk_and_leaves_unrest_to_the_scene() -> None:
    result = _negotiate(_world(), _scenario())
    assert result.world.uprisings == []
    assert result.world.regions[HOME].unrest == 80
    assert len(result.world.revolt_talk_queue) == 1


def test_negotiate_keeps_the_flat_cut_when_talks_are_off() -> None:
    result = _negotiate(_world(), _scenario(is_enabled=False))
    assert result.world.regions[HOME].unrest == 60
    assert result.world.revolt_talk_queue == []


def test_arming_opens_the_queued_talk_as_a_scene() -> None:
    world, scene_id = _armed_world(_scenario())
    assert scene_id == revolt_scene_id(world, HOME)
    assert world.progress.pending_revolt_talk is not None
    assert world.revolt_talk_queue == []


def test_arming_drops_a_talk_whose_region_changed_hands() -> None:
    scenario = _scenario()
    world = _negotiate(_world(), scenario).world
    world.regions[HOME].owner_id = None
    arm_revolt_talk(world, scenario)
    assert world.progress.pending_scene_id is None
    assert world.revolt_talk_queue == []


def test_charter_cuts_unrest_signs_two_covenants_and_sets_low_taxes() -> None:
    scenario = _scenario()
    world, scene_id = _armed_world(scenario)
    world.factions[PLAYER].tax_rate = TaxRate.NORMAL
    closed, events = close_revolt_talk(
        world, scenario, scene_id, ChoiceOutcome(option_id="charter")
    )
    assert closed.regions[HOME].unrest == 30
    assert closed.factions[PLAYER].tax_rate is TaxRate.LOW
    assert {item.covenant for item in closed.covenants} == {
        CovenantKind.TAX_RELIEF,
        CovenantKind.GARRISON_OUT,
    }
    assert closed.progress.pending_scene_id is None
    assert [event.kind for event in events].count("covenant_made") == 2


def test_relief_payment_spends_the_treasury_without_a_covenant() -> None:
    scenario = _scenario()
    world, scene_id = _armed_world(scenario)
    closed, _ = close_revolt_talk(
        world, scenario, scene_id, ChoiceOutcome(option_id="relief_large")
    )
    assert closed.factions[PLAYER].treasury == GOLD - 80
    assert closed.covenants == []


def test_an_unaffordable_option_is_refused() -> None:
    scenario = _scenario()
    world, scene_id = _armed_world(scenario)
    world.factions[PLAYER].treasury = 10
    with pytest.raises(CampaignProgressError):
        close_revolt_talk(
            world, scenario, scene_id, ChoiceOutcome(option_id="relief_large")
        )


def test_words_alone_give_the_flat_unrest_cut() -> None:
    scenario = _scenario()
    world, scene_id = _armed_world(scenario)
    closed, _ = close_revolt_talk(
        world, scenario, scene_id, ChoiceOutcome(option_id="no_terms")
    )
    assert closed.regions[HOME].unrest == 60
    assert closed.covenants == []


def _chartered(scenario):
    world, scene_id = _armed_world(scenario)
    closed, _ = close_revolt_talk(
        world, scenario, scene_id, ChoiceOutcome(option_id="charter")
    )
    return closed


def test_raising_taxes_breaks_the_charter_and_reignites_the_revolt() -> None:
    scenario = _scenario()
    world = _chartered(scenario)
    world.factions[PLAYER].tax_rate = TaxRate.HIGH
    events = scan_covenants(world, scenario, [], PhaseName.INTERNAL)
    assert [event.kind for event in events] == ["covenant_broken"]
    assert world.covenants[0].status is CovenantStatus.BREACHED
    assert world.uprisings[0].stage.value == "riot"
    assert world.revolt_lockouts[HOME] > world.clock.turn
    assert world.regions[HOME].unrest == 50


def test_a_broken_covenant_locks_the_region_out_of_talks() -> None:
    scenario = _scenario()
    world = _chartered(scenario)
    world.factions[PLAYER].tax_rate = TaxRate.HIGH
    scan_covenants(world, scenario, [], PhaseName.INTERNAL)
    with pytest.raises(CommandError):
        _negotiate(world, scenario, "talk-again")


def test_a_kept_covenant_is_fulfilled_after_its_term() -> None:
    scenario = _scenario()
    world = _chartered(scenario)
    world.clock.turn = world.covenants[0].end_turn + 1
    scan_covenants(world, scenario, [], PhaseName.INTERNAL)
    assert {item.status for item in world.covenants} == {CovenantStatus.FULFILLED}


def test_closing_a_talk_replays_to_the_same_hash() -> None:
    scenario = _scenario()
    world, scene_id = _armed_world(scenario)
    first, _ = close_revolt_talk(
        world, scenario, scene_id, ChoiceOutcome(option_id="charter")
    )
    second, _ = close_revolt_talk(
        world, scenario, scene_id, ChoiceOutcome(option_id="charter")
    )
    assert world_hash(first) == world_hash(second)


def test_an_empty_revolt_state_is_omitted_from_the_world_document() -> None:
    document = _world().model_dump(mode="json")
    for key in ("revolt_talk_queue", "revolt_lockouts", "covenants"):
        assert key not in document


def test_a_lifecycle_world_queues_the_talk_in_the_internal_phase() -> None:
    scenario = _scenario()
    world = _world()
    world.internal_ruleset = 2
    queued = _negotiate(world, scenario).world
    assert queued.revolt_talk_queue == []
    apply_queued_responses(
        queued, scenario.tuning.internal, scenario.tuning.revolt_talk
    )
    assert len(queued.revolt_talk_queue) == 1
