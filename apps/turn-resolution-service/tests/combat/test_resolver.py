"""Provider-free contracts for deterministic character combat."""

import uuid

import pytest
from app.combat.models import CombatAction, Combatant, CombatState
from app.combat.resolver import legal_actions, resolve_action, start_combat
from pydantic import ValidationError


def actor(actor_id, side, **overrides):
    values = {
        "actor_id": actor_id,
        "side": side,
        "max_health": 20,
        "health": 20,
        "attack": 9,
        "armor": 4,
        "speed": 5,
        "accuracy": 70,
        "luck": 50,
    }
    return Combatant(**(values | overrides))


def action(state, actor_id, target_id):
    return CombatAction(
        client_action_id=uuid.UUID(int=1),
        expected_revision=state.revision,
        actor_id=actor_id,
        action_id="attack",
        target_id=target_id,
    )


def test_turn_order_and_stable_ties():
    state = start_combat("test", actor("z", "player"), actor("a", "opponent"))
    assert state.turn_order == ("a", "z")
    assert state.current_actor_id == "a"
    state = resolve_action(state, action(state, "a", "z")).state
    assert state.current_actor_id == "z"
    state = resolve_action(state, action(state, "z", "a")).state
    assert (state.current_actor_id, state.round_number) == ("a", 2)


def test_luck_accumulator_is_deterministic_and_replayable():
    state = start_combat("test", actor("a", "player"), actor("z", "opponent"))
    results = []
    for _ in range(5):
        target = "z" if state.current_actor_id == "a" else "a"
        transition = resolve_action(
            state, action(state, state.current_actor_id, target)
        )
        results.append(transition.event.hit)
        state = transition.state
    assert results == [False, False, True, True, True]
    start = start_combat("test", actor("a", "player"), actor("z", "opponent"))
    assert resolve_action(start, action(start, "a", "z")) == resolve_action(
        start, action(start, "a", "z")
    )


def test_damage_luck_health_clamp_and_no_mutation():
    player = actor("a", "player", accuracy=100, luck=60)
    enemy = actor("z", "opponent", health=3, luck=40)
    before = start_combat("test", player, enemy)
    transition = resolve_action(before, action(before, "a", "z"))
    assert transition.event.damage == 3
    assert transition.state.combatants[1].health == 0
    assert transition.state.status == "opponent_defeated"
    assert before.combatants[1].health == 3
    assert before.revision == 0


def test_negative_luck_division_truncates_toward_zero():
    state = start_combat(
        "test",
        actor("a", "player", accuracy=100, luck=49),
        actor("z", "opponent", luck=50),
    )
    state = resolve_action(state, action(state, "a", "z")).state
    state = resolve_action(state, action(state, "z", "a")).state
    result = resolve_action(state, action(state, "a", "z"))
    assert result.event.hit and result.event.damage == 5


def test_player_zero_ends_combat_only():
    state = start_combat(
        "test",
        actor("a", "player", health=2),
        actor("z", "opponent", speed=10, accuracy=100),
    )
    result = resolve_action(state, action(state, "z", "a"))
    assert result.event.damage == 2
    assert result.state.status == "player_defeated"
    assert result.state.current_actor_id is None
    assert legal_actions(result.state, "a") == ()


def test_authored_immunity_and_unwinnable_loadout():
    player = actor(
        "a",
        "player",
        accuracy=100,
        attack_tags=frozenset({"trelium"}),
        required_attack_tag="trelium",
    )
    enemy = actor(
        "z", "opponent", required_attack_tag="trelium", speed=10, accuracy=100
    )
    state = start_combat("test", player, enemy)
    result = resolve_action(state, action(state, "z", "a"))
    assert result.event.hit and result.event.immune and result.event.damage == 0
    assert result.state.combatants[0].health == 20
    with pytest.raises(ValueError):
        start_combat("test", actor("a", "player"), enemy)


def test_illegal_and_stale_actions_do_not_change_state():
    state = start_combat("test", actor("a", "player"), actor("z", "opponent"))
    stale = action(state, "a", "z").model_copy(update={"expected_revision": 7})
    for request in [
        action(state, "z", "a"),
        action(state, "a", "a"),
        action(state, "a", "missing"),
        stale,
    ]:
        with pytest.raises(ValueError):
            resolve_action(state, request)
    assert state.revision == 0
    assert legal_actions(state, "z") == ()


@pytest.mark.parametrize(
    "overrides",
    [
        {"luck": 101},
        {"health": 21},
        {"max_health": 0},
        {"attack": True},
        {"accuracy": -1},
    ],
)
def test_invalid_stats_rejected(overrides):
    with pytest.raises(ValidationError):
        actor("a", "player", **overrides)


def test_encounter_starts_accumulators_at_zero():
    player = actor("a", "player", hit_accumulator=70)
    state = start_combat("test", player, actor("z", "opponent"))
    assert state.combatants[0].hit_accumulator == 0


def test_terminal_state_matches_the_defeated_actor():
    state = start_combat("test", actor("a", "player"), actor("z", "opponent"))
    invalid = state.model_dump()
    invalid.update(status="player_defeated", current_actor_id=None)
    with pytest.raises(ValidationError):
        CombatState.model_validate(invalid)


def test_forged_turn_order_is_rejected():
    state = start_combat("test", actor("a", "player", speed=10), actor("z", "opponent"))
    invalid = state.model_dump()
    invalid.update(turn_order=("z", "a"), current_actor_id="z")
    with pytest.raises(ValidationError):
        CombatState.model_validate(invalid)


def test_reloaded_state_preserves_luck_progress():
    original = start_combat("test", actor("a", "player"), actor("z", "opponent"))
    original = resolve_action(original, action(original, "a", "z")).state
    reloaded = CombatState.model_validate_json(original.model_dump_json())
    request = action(original, "z", "a")
    assert resolve_action(original, request) == resolve_action(reloaded, request)
    assert reloaded.combatants[0].hit_accumulator == 70


def test_minimum_accuracy_eventually_hits_without_random_draws():
    player = actor("a", "player", max_health=1000, health=1000, accuracy=0, luck=0)
    enemy = actor("z", "opponent", max_health=100, health=100, luck=100, attack=0)
    state = start_combat("test", player, enemy)
    hits = []
    for _ in range(20):
        result = resolve_action(state, action(state, "a", "z"))
        hits.append(result.event.hit)
        state = resolve_action(result.state, action(result.state, "z", "a")).state
    assert hits == [False] * 19 + [True]


def test_attack_tags_serialize_in_stable_order():
    player = actor("a", "player", attack_tags=frozenset({"zinc", "iron", "trelium"}))
    state = start_combat("test", player, actor("z", "opponent"))
    assert state.model_dump(mode="json")["combatants"][0]["attack_tags"] == [
        "iron",
        "trelium",
        "zinc",
    ]
