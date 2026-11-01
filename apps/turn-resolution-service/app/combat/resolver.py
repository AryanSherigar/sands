"""Pure deterministic hit, damage, and turn progression for normal play."""

from app.combat.models import (
    CombatAction,
    Combatant,
    CombatEvent,
    CombatState,
    CombatTransition,
    LegalAttack,
)

HIT_SCALE = 100
MIN_HIT_CHANCE = 5
LUCK_DAMAGE_DIVISOR = 10


def start_combat(
    encounter_id: str, player: Combatant, opponent: Combatant
) -> CombatState:
    if player.side != "player" or opponent.side != "opponent":
        raise ValueError("encounter needs a player and an opponent")
    if player.health == 0 or opponent.health == 0:
        raise ValueError("encounter cannot begin with a defeated combatant")
    if (
        opponent.required_attack_tag
        and opponent.required_attack_tag not in player.attack_tags
    ):
        raise ValueError("player cannot damage the opponent")
    player = player.model_copy(update={"hit_accumulator": 0})
    opponent = opponent.model_copy(update={"hit_accumulator": 0})
    order = tuple(
        item.actor_id
        for item in sorted(
            (player, opponent), key=lambda item: (-item.speed, item.actor_id)
        )
    )
    return CombatState(
        encounter_id=encounter_id,
        combatants=(player, opponent),
        turn_order=order,
        current_actor_id=order[0],
    )


def legal_actions(state: CombatState, actor_id: str) -> tuple[LegalAttack, ...]:
    if state.status != "active" or state.current_actor_id != actor_id:
        return ()
    target = next(
        (item for item in state.combatants if item.actor_id != actor_id), None
    )
    if target is None or target.health == 0:
        return ()
    return (LegalAttack(actor_id=actor_id, target_id=target.actor_id),)


def _hit(attacker: Combatant, defender: Combatant) -> tuple[bool, int]:
    chance = max(
        MIN_HIT_CHANCE,
        min(HIT_SCALE, attacker.accuracy + attacker.luck - defender.luck),
    )
    total = attacker.hit_accumulator + chance
    return (True, total - HIT_SCALE) if total >= HIT_SCALE else (False, total)


def _damage(attacker: Combatant, defender: Combatant) -> int:
    difference = attacker.luck - defender.luck
    magnitude = abs(difference) // LUCK_DAMAGE_DIVISOR
    luck_damage = magnitude if difference >= 0 else -magnitude
    return min(defender.health, max(1, attacker.attack - defender.armor + luck_damage))


def _actor(state: CombatState, actor_id: str) -> Combatant:
    return next(item for item in state.combatants if item.actor_id == actor_id)


def resolve_action(state: CombatState, action: CombatAction) -> CombatTransition:
    if action.expected_revision != state.revision:
        raise ValueError("stale combat revision")
    allowed = legal_actions(state, action.actor_id)
    if (
        not allowed
        or action.action_id != "attack"
        or allowed[0].target_id != action.target_id
    ):
        raise ValueError("illegal combat action")
    attacker, defender = _actor(state, action.actor_id), _actor(state, action.target_id)
    hit, accumulator = _hit(attacker, defender)
    immune = bool(
        hit
        and defender.required_attack_tag
        and defender.required_attack_tag not in attacker.attack_tags
    )
    damage = _damage(attacker, defender) if hit and not immune else 0
    new_attacker = attacker.model_copy(update={"hit_accumulator": accumulator})
    new_defender = defender.model_copy(update={"health": defender.health - damage})
    combatants = tuple(
        new_attacker if item.actor_id == attacker.actor_id else new_defender
        for item in state.combatants
    )
    defeated = new_defender.health == 0
    status = f"{defender.side}_defeated" if defeated else "active"
    turn_index = state.turn_order.index(attacker.actor_id)
    next_actor = (
        None if defeated else state.turn_order[(turn_index + 1) % len(state.turn_order)]
    )
    next_round = state.round_number + int(
        not defeated and turn_index == len(state.turn_order) - 1
    )
    updated = CombatState(
        encounter_id=state.encounter_id,
        rules_version=state.rules_version,
        revision=state.revision + 1,
        round_number=next_round,
        status=status,
        combatants=combatants,
        turn_order=state.turn_order,
        current_actor_id=next_actor,
    )
    event = CombatEvent(
        actor_id=attacker.actor_id,
        target_id=defender.actor_id,
        hit=hit,
        immune=immune,
        damage=damage,
        target_health=new_defender.health,
    )
    return CombatTransition(state=updated, event=event)
