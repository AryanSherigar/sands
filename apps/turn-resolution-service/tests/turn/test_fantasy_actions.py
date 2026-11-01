import pytest
from app.exceptions.fantasy_exceptions import FantasyActionError
from app.turn.fantasy_rules import resolve_fantasy_action, resolve_mission_event


@pytest.fixture
def config():
    return {
        "version": 1,
        "profile": "zegaris",
        "energy_max": 100,
        "initial_energy": 60,
        "rest_cost": 5,
        "bounty_reward": 8,
        "locations": {
            "inn": "inn",
            "quest_giver": "hall",
            "recovery": "shaft",
            "cremation": "pyre",
        },
        "corpse_item_id": "body",
        "class_loadouts": {},
    }


def make_state(coins=10, energy=25, stage="offered", location="inn", inventory=None):
    return {
        "player": {"coins": coins, "energy": energy, "inventory": inventory or []},
        "quests": {"retrieval": {"stage": stage}},
        "current_location_id": location,
    }


def test_rest_applies_payment_and_recovery_together(config):
    original = make_state()
    result = resolve_fantasy_action(original, config, "rest")
    assert result["player"]["coins"] == 5
    assert result["player"]["energy"] == 100
    assert original["player"]["coins"] == 10
    assert original["player"]["energy"] == 25


@pytest.mark.parametrize("state", [make_state(coins=4), make_state(location="hall")])
def test_rest_rejects_without_changing_original(config, state):
    with pytest.raises(FantasyActionError):
        resolve_fantasy_action(state, config, "rest")
    assert state["player"]["energy"] == 25


def test_reward_is_single_use_and_requires_cremation(config):
    state = make_state(stage="cremated", location="hall")
    result = resolve_fantasy_action(state, config, "claim_retrieval_reward")
    assert result["player"]["coins"] == 18
    assert result["quests"]["retrieval"]["stage"] == "rewarded"
    with pytest.raises(FantasyActionError):
        resolve_fantasy_action(result, config, "claim_retrieval_reward")


def test_null_reward_refuses_claim(config):
    config["bounty_reward"] = None
    with pytest.raises(FantasyActionError):
        resolve_fantasy_action(
            make_state(stage="cremated", location="hall"),
            config,
            "claim_retrieval_reward",
        )


def test_mission_advances_only_in_order_and_moves_the_body(config):
    offered = make_state(location="hall")
    accepted = resolve_mission_event(offered, config, "accept_retrieval")
    assert accepted["quests"]["retrieval"]["stage"] == "accepted"
    accepted["current_location_id"] = "shaft"
    recovered = resolve_mission_event(accepted, config, "recover_body")
    assert recovered["player"]["inventory"] == ["body"]
    assert recovered["quests"]["retrieval"]["stage"] == "body_recovered"
    recovered["current_location_id"] = "pyre"
    cremated = resolve_mission_event(recovered, config, "cremate_body")
    assert cremated["player"]["inventory"] == []
    assert cremated["quests"]["retrieval"]["stage"] == "cremated"


def test_mission_skips_and_missing_body_are_rejected(config):
    with pytest.raises(FantasyActionError):
        resolve_mission_event(make_state(location="shaft"), config, "recover_body")
    with pytest.raises(FantasyActionError):
        resolve_mission_event(
            make_state(stage="body_recovered", location="pyre"), config, "cremate_body"
        )


def test_mission_tool_is_profile_gated_and_validates_transition(config):
    from app.models.tool_call import MasterModeTurnResult
    from app.turn.steps.ai_orchestrator import _apply_function_calls
    from app.turn.tool_definitions import build_master_mode_tools
    from google.genai import types

    schema = {
        "player": {
            "type": "object",
            "fields": {
                "coins": {"type": "number"},
                "energy": {"type": "number"},
                "inventory": {"type": "list"},
            },
        },
        "quests": {
            "type": "object",
            "fields": {
                "retrieval": {
                    "type": "object",
                    "fields": {"stage": {"type": "string"}},
                },
            },
        },
    }
    snapshot = {"mode": "master", "fantasy_mechanics": config, "state_schema": schema}
    names = [
        item.name for item in build_master_mode_tools(snapshot).function_declarations
    ]
    assert "propose_retrieval_event" in names
    assert "propose_retrieval_event" not in [
        item.name for item in build_master_mode_tools({}).function_declarations
    ]
    call = types.FunctionCall(
        name="propose_retrieval_event", args={"event": "recover_body"}
    )
    sink = MasterModeTurnResult()
    original = make_state(stage="accepted", location="shaft")
    result = _apply_function_calls([call], original, snapshot, sink)
    assert result["quests"]["retrieval"]["stage"] == "body_recovered"
    assert result["player"]["inventory"] == ["body"]
    assert original["player"]["inventory"] == []
    assert sink.tool_calls[0].is_valid
    rejected = MasterModeTurnResult()
    assert _apply_function_calls([call], result, snapshot, rejected) == result
    assert not rejected.tool_calls[0].is_valid


def test_generic_mutations_cannot_change_protected_fantasy_state(config):
    from app.models.tool_call import ProposedMutation
    from app.turn.steps.state_validator import validate_mutation

    snapshot = {"fantasy_mechanics": config}
    state = make_state(inventory=["rope", "body"])
    for path, value in [
        ("player.coins", 99),
        ("player.energy", 100),
        ("quests.retrieval.stage", "rewarded"),
        ("player", {}),
        ("player.inventory", ["rope"]),
    ]:
        mutation = ProposedMutation(
            tool_name="set_field", op="set", path=path, value=value
        )
        result = validate_mutation(mutation, state, snapshot)
        assert not result.is_valid, path
        assert "system-managed" in result.error_message


def test_condition_mutations_cannot_change_protected_state(config):
    from app.turn.steps.state_validator import validate_applied_change

    state = make_state()
    candidate = make_state(coins=0)
    result = validate_applied_change(
        "player.coins", candidate, {"fantasy_mechanics": config}, original_state=state
    )
    assert not result.is_valid
    assert "system-managed" in result.error_message


def test_structured_request_requires_matching_action_kind():
    import uuid

    from app.models.turn import TurnRequestInput
    from pydantic import ValidationError

    base = {
        "playthrough_id": uuid.uuid4(),
        "participant_id": uuid.uuid4(),
        "client_action_id": uuid.uuid4(),
        "action_text": "",
    }
    request = TurnRequestInput(
        **base, action_kind="fantasy_action", fantasy_action={"action_id": "rest"}
    )
    assert request.fantasy_action.action_id == "rest"
    with pytest.raises(ValidationError):
        TurnRequestInput(**base, action_kind="fantasy_action")
    with pytest.raises(ValidationError):
        TurnRequestInput(**base, fantasy_action={"action_id": "rest"})
    with pytest.raises(ValidationError):
        TurnRequestInput(
            **base,
            action_kind="fantasy_action",
            fantasy_action={"action_id": "rest", "price": 0},
        )


def test_action_resolver_rejects_whole_transition_on_invariant_failure(config):
    import uuid

    from app.models.turn import LoadedState, TurnRequest
    from app.turn.pipeline import _resolve_fantasy_intake

    state = make_state()
    snapshot = {
        "mode": "master",
        "fantasy_mechanics": config,
        "state_schema": {
            "player": {
                "type": "object",
                "fields": {
                    "coins": {"type": "number"},
                    "energy": {"type": "number"},
                    "inventory": {"type": "list"},
                },
            },
            "quests": {
                "type": "object",
                "fields": {
                    "retrieval": {
                        "type": "object",
                        "fields": {"stage": {"type": "string"}},
                    }
                },
            },
        },
        "rule_invariants": [
            {
                "invariant_expression": {
                    "op": ">=",
                    "field": "player.coins",
                    "value": 10,
                },
                "narrator_text": "Minimum balance",
            }
        ],
    }
    with pytest.raises(FantasyActionError):
        _resolve_fantasy_intake(
            TurnRequest(
                playthrough_id=uuid.uuid4(),
                participant_id=uuid.uuid4(),
                client_action_id=uuid.uuid4(),
                action_text="",
                action_kind="fantasy_action",
                fantasy_action={"action_id": "rest"},
                turn_count=0,
            ),
            LoadedState(
                scenario_id=uuid.uuid4(),
                scenario_snapshot=snapshot,
                state=state,
                turn_count=0,
                checkpoint=None,
            ),
        )
    assert state["player"]["coins"] == 10
    assert state["player"]["energy"] == 25
