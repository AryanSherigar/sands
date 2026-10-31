import pytest
from app.engine.commands.phases import CampaignSiegePhase
from app.engine.commands.timing import owning_phase
from app.engine.commands.validation import validate_empire_command
from app.engine.sieges.orders import apply_besiege, validate_besiege
from app.exceptions.command_exceptions import CommandError
from app.models.battle_command import CommandStatus
from app.models.orders import BesiegeOrder
from app.models.world_battle import BattleState
from app.models.world_diplomacy import RelationStatus
from app.models.world_siege import SiegeState
from app.models.world_state import WorldState

from tests.engine.diplomacy.builders import queue_npc_order
from tests.engine.sieges.builders import (
    BESIEGER,
    BESIEGER_ARMY,
    SCENARIO,
    TARGET_REGION,
    make_siege_world,
    occupy,
    run_phase,
)


def _order(region_id: str = TARGET_REGION) -> BesiegeOrder:
    return BesiegeOrder(
        faction_id=BESIEGER, army_id=BESIEGER_ARMY, target_region_id=region_id
    )


def _reason(world: WorldState, order: BesiegeOrder) -> str:
    with pytest.raises(CommandError) as raised:
        validate_besiege(world, order)
    assert raised.value.status_code == 422
    return raised.value.code


def test_a_valid_besiege_order_passes() -> None:
    validate_besiege(make_siege_world(), _order())


def test_besiege_needs_the_siege_ruleset() -> None:
    world = make_siege_world()
    world.siege_ruleset = 0

    assert _reason(world, _order()) == "siege_not_enabled"


def test_target_must_be_the_armys_region() -> None:
    assert _reason(make_siege_world(), _order("ashford")) == "wrong_region"


def test_cannot_besiege_your_own_region() -> None:
    world = make_siege_world()
    world.regions[TARGET_REGION].owner_id = BESIEGER

    assert _reason(world, _order()) == "own_region"


def test_cannot_besiege_an_unowned_region() -> None:
    world = make_siege_world()
    world.regions[TARGET_REGION].owner_id = None

    assert _reason(world, _order()) == "no_owner"


def test_cannot_besiege_without_a_war() -> None:
    world = make_siege_world()
    for relation in world.relations:
        relation.status = RelationStatus.PEACE

    assert _reason(world, _order()) == "not_at_war"


def test_an_army_in_an_open_battle_cannot_besiege() -> None:
    world = make_siege_world()
    world.battles.append(
        BattleState(
            id="battle_open",
            region_id=TARGET_REGION,
            attacker_army_ids=[BESIEGER_ARMY],
            defender_army_ids=[],
        )
    )

    assert _reason(world, _order()) == "army_in_battle"


def test_cannot_besiege_an_occupied_region() -> None:
    world = make_siege_world()
    occupy(world)

    assert _reason(world, _order()) == "already_occupied"


def test_cannot_besiege_a_region_another_faction_is_besieging() -> None:
    world = make_siege_world()
    world.sieges.append(
        SiegeState(region_id=TARGET_REGION, besieger_id="house_dunwick", army_ids=[])
    )

    assert _reason(world, _order()) == "already_besieged"


def test_besiege_starts_a_siege_without_a_battle() -> None:
    world = make_siege_world()

    events = apply_besiege(world, _order())

    assert [siege.region_id for siege in world.sieges] == [TARGET_REGION]
    assert [event.kind for event in events] == ["siege_started"]


def test_a_second_army_joins_the_existing_siege() -> None:
    world = make_siege_world()
    apply_besiege(world, _order())
    world.armies["army_ashford_2"].location_id = TARGET_REGION

    events = apply_besiege(
        world,
        BesiegeOrder(
            faction_id=BESIEGER,
            army_id="army_ashford_2",
            target_region_id=TARGET_REGION,
        ),
    )

    assert events == []
    assert world.sieges[0].army_ids == ["army_ashford_1", "army_ashford_2"]


def test_besiege_is_owned_by_the_sieges_phase() -> None:
    world = make_siege_world()
    accepted = queue_npc_order(world, SCENARIO, _order())

    assert owning_phase(accepted.accepted_commands[-1]) == "sieges"


def test_empire_command_validation_covers_besiege() -> None:
    world = make_siege_world()
    world.regions[TARGET_REGION].owner_id = BESIEGER

    with pytest.raises(CommandError) as raised:
        validate_empire_command(world, _order(), SCENARIO)

    assert raised.value.code == "own_region"


def test_the_campaign_phase_applies_a_queued_besiege_order() -> None:
    world = queue_npc_order(make_siege_world(), SCENARIO, _order())

    result = run_phase(CampaignSiegePhase(), world)

    command = result.world.accepted_commands[-1]
    assert command.status is CommandStatus.APPLIED
    assert [siege.region_id for siege in result.world.sieges] == [TARGET_REGION]
    assert result.world.sieges[0].progress > 0


def test_the_campaign_phase_fails_an_order_that_became_invalid() -> None:
    world = queue_npc_order(make_siege_world(), SCENARIO, _order())
    for relation in world.relations:
        relation.status = RelationStatus.PEACE

    result = run_phase(CampaignSiegePhase(), world)

    assert result.world.accepted_commands[-1].status is CommandStatus.FAILED
    assert result.world.sieges == []
