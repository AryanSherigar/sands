import importlib

import pytest
from pydantic import ValidationError


def test_deployment_partitions_available_troops() -> None:
    deployment_type = importlib.import_module("app.models.world_battle").ArmyDeployment
    deployment = deployment_type(
        army_id="army_a",
        available={"infantry": 100},
        active={"infantry": 60},
        reserve={"infantry": 40},
    )
    assert sum(deployment.active.values()) + sum(deployment.reserve.values()) == 100
    with pytest.raises(ValidationError):
        deployment_type(
            army_id="army_a",
            available={"infantry": 100},
            active={"infantry": 80},
            reserve={"infantry": 40},
        )


def test_standing_plan_rejects_unsupported_tactic() -> None:
    plan_type = importlib.import_module("app.models.world_battle").StandingPlan
    with pytest.raises(ValidationError):
        plan_type(tactic="ambush")
    assert plan_type().tactic == "hold"


def test_troop_captive_requires_origin_and_reconciled_types() -> None:
    from app.models.world_diplomacy import PrisonerState

    payload = dict(
        id="p1", held_by_id="aa", origin_faction_id="bb", kind="troops", troop_count=40
    )
    with pytest.raises(ValidationError):
        PrisonerState(**payload)
    prisoner = PrisonerState(
        **payload, origin_battle_id="battle_1", troops_by_type={"infantry": 40}
    )
    assert prisoner.troop_count == 40
    with pytest.raises(ValidationError):
        PrisonerState(
            **payload, origin_battle_id="battle_1", troops_by_type={"infantry": 39}
        )


def test_character_captive_rejects_troop_fields() -> None:
    from app.models.world_diplomacy import PrisonerState

    with pytest.raises(ValidationError):
        PrisonerState(
            id="p1",
            held_by_id="aa",
            origin_faction_id="bb",
            kind="character",
            character_id="commander_a",
            troop_count=2,
        )


def test_accepted_command_round_trips_typed_payload_and_checks_identity() -> None:
    from app.models.battle_command import AcceptedCommand, SetPlanCommand
    from app.models.world_battle import StandingPlan

    command = AcceptedCommand(
        id="command_1",
        operation_id="op1",
        actor_id="actor_1",
        faction_id="aa",
        battle_id="battle_1",
        accepted_turn=2,
        accepted_wave=1,
        execution_turn=2,
        execution_wave=1,
        reserved_cost=1,
        command=SetPlanCommand(
            faction_id="aa", battle_id="battle_1", plan=StandingPlan()
        ),
    )
    restored = AcceptedCommand.model_validate_json(command.model_dump_json())
    assert isinstance(restored.command, SetPlanCommand)
    with pytest.raises(ValidationError):
        AcceptedCommand.model_validate({**command.model_dump(), "faction_id": "bb"})
    with pytest.raises(ValidationError):
        AcceptedCommand.model_validate({**command.model_dump(), "execution_turn": 1})


def test_recon_report_bounds_and_unknown_fields_are_rejected() -> None:
    from app.models.battle_intelligence import ReconReport

    payload = dict(
        id="report_1",
        battle_id="battle_1",
        observer_faction_id="aa",
        subject_faction_id="bb",
        mission_id="mission_1",
        target="composition",
        observed_turn=2,
        observed_exchange=1,
        available_from_wave=2,
        strength={"minimum": 10, "maximum": 20},
        confidence="high",
    )
    assert ReconReport(**payload).strength.maximum == 20
    with pytest.raises(ValidationError):
        ReconReport(**{**payload, "strength": {"minimum": 20, "maximum": 10}})
    with pytest.raises(ValidationError):
        ReconReport(**payload, is_truthful=True)


def test_world_has_one_battle_store_and_rejects_duplicate_active_membership() -> None:
    from app.models.world_battle import BattleState
    from app.models.world_state import WorldState

    from tests.models.builders import make_world

    world = make_world()
    world.battles.append(
        BattleState(
            id="battle_1",
            region_id="ashford",
            attacker_army_ids=["army_a"],
            defender_army_ids=[],
        )
    )
    assert world.pending_battles is world.battles
    document = world.model_dump()
    document["battles"].append({**document["battles"][0], "id": "battle_2"})
    with pytest.raises(ValidationError):
        WorldState.model_validate(document)


@pytest.mark.parametrize("fatigue", [-1, 101])
def test_army_fatigue_bounds_are_enforced(fatigue: int) -> None:
    from app.models.world_army import ArmyState

    with pytest.raises(ValidationError):
        ArmyState(
            id="army_a",
            owner_id="aa",
            troops={"infantry": 100},
            morale=70,
            location_id="ashford",
            fatigue=fatigue,
        )


def test_accepted_command_cannot_execute_an_earlier_wave() -> None:
    from app.models.battle_command import AcceptedCommand

    payload = dict(
        id="command_1",
        operation_id="op1",
        actor_id="actor_1",
        faction_id="aa",
        battle_id="battle_1",
        accepted_turn=2,
        accepted_wave=2,
        execution_turn=2,
        execution_wave=1,
        reserved_cost=1,
        command={"kind": "withdraw", "faction_id": "aa", "battle_id": "battle_1"},
    )
    with pytest.raises(ValidationError):
        AcceptedCommand(**payload)


def test_public_battle_menu_rejects_unsupported_commands() -> None:
    from app.models.world_battle import BattleView

    with pytest.raises(ValidationError):
        BattleView(
            id="battle_1",
            region_id="ashford",
            status="awaiting_commands",
            outcome=None,
            current_turn=2,
            exchanges_used=0,
            total_exchanges=0,
            terrain="plain",
            weather="clear",
            legal_commands=["ambush"],
        )


def test_battle_rejects_army_shared_by_different_contingents() -> None:
    from app.models.world_battle import BattleState

    with pytest.raises(ValidationError, match="more than one contingent"):
        BattleState.model_validate(
            {
                "id": "battle_1",
                "region_id": "ashford",
                "attacker_army_ids": ["army_a"],
                "defender_army_ids": [],
                "contingents": {
                    "house_ashford": {
                        "faction_id": "house_ashford",
                        "side": "attacker",
                        "army_ids": ["army_a"],
                        "entry_troops": 100,
                    },
                    "house_carrow": {
                        "faction_id": "house_carrow",
                        "side": "attacker",
                        "army_ids": ["army_a"],
                        "entry_troops": 100,
                    },
                },
            }
        )


def test_world_rejects_contingent_claiming_another_factions_army() -> None:
    from app.models.world_state import WorldState

    from tests.models.builders import make_world

    document = make_world().model_dump()
    document["battles"] = [
        {
            "id": "battle_1",
            "region_id": "ashford",
            "attacker_army_ids": ["army_a"],
            "defender_army_ids": [],
            "contingents": {
                "house_carrow": {
                    "faction_id": "house_carrow",
                    "side": "attacker",
                    "army_ids": ["army_a"],
                    "entry_troops": 100,
                }
            },
        }
    ]
    with pytest.raises(ValidationError, match="contingent faction must own its army"):
        WorldState.model_validate(document)
