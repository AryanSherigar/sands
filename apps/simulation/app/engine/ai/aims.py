from dataclasses import dataclass

from app.engine.ai.events import stamp_ai_event
from app.engine.ai.scoring import stance_score, trait_score
from app.engine.ai.situation import is_hostile, war_enemies
from app.engine.ai.temperament import temperament_bias
from app.engine.rng import DeterministicRng
from app.models.world_ai import AimState
from app.models.world_character import LeaderState
from app.models.world_events import EventCause, EventLogEntry
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.stances import ScoreCategory

AIM_SET_KIND = "ai_aim_set"
GROUND_HISTORY_DIVISOR = 10
GROUND_HISTORY_CAP = 10


@dataclass(frozen=True)
class AimChoice:
    aim: AimState
    score: int


def _strongest_ground_target(
    world: WorldState, faction_id: FactionId
) -> FactionId | None:
    held = [item for item in world.grounds if item.holder_faction_id == faction_id]
    if not held:
        return None
    strongest = max(held, key=lambda item: (item.strength, item.id))
    return strongest.target_faction_id


def _worst_opinion_target(world: WorldState, leader: LeaderState) -> FactionId | None:
    ranked = sorted(
        (sum(reason.value for reason in opinion.reasons), target_id)
        for target_id, opinion in leader.opinions.items()
        if target_id in world.leaders
    )
    if not ranked or ranked[0][0] >= 0:
        return None
    return world.leaders[ranked[0][1]].faction_id


def pick_target(world: WorldState, faction_id: FactionId) -> FactionId | None:
    enemies = war_enemies(world, faction_id)
    if enemies:
        return enemies[0]
    ground_target = _strongest_ground_target(world, faction_id)
    if ground_target is not None:
        return ground_target
    leader_id = world.factions[faction_id].leader_id
    if leader_id is None or leader_id not in world.leaders:
        return None
    return _worst_opinion_target(world, world.leaders[leader_id])


def pick_ally_target(world: WorldState, faction_id: FactionId) -> FactionId | None:
    leader_id = world.factions[faction_id].leader_id
    if leader_id is None or leader_id not in world.leaders:
        return None
    enemies = set(war_enemies(world, faction_id))
    ranked = sorted(
        (
            -sum(reason.value for reason in opinion.reasons),
            world.leaders[other].faction_id,
        )
        for other, opinion in world.leaders[leader_id].opinions.items()
        if other in world.leaders
    )
    for negative_warmth, other_faction_id in ranked:
        other = world.factions.get(other_faction_id)
        if negative_warmth >= 0 or other is None:
            continue
        if not (other.is_player or other.is_destroyed or other_faction_id in enemies):
            return other_faction_id
    return None


def _aim_target(
    world: WorldState,
    faction_id: FactionId,
    category: ScoreCategory,
    attack_target: FactionId | None,
) -> FactionId | None:
    if category == ScoreCategory.ATTACK:
        return attack_target
    if category == ScoreCategory.ALLY:
        return pick_ally_target(world, faction_id)
    return None


def _holds_capital(world: WorldState, faction_id: FactionId) -> bool:
    capital_id = world.factions[faction_id].capital_region_id
    return capital_id is None or world.regions[capital_id].owner_id == faction_id


def aim_is_valid(
    world: WorldState, scenario: StrategyScenario, faction_id: FactionId, aim: AimState
) -> bool:
    faction = world.factions[faction_id]
    target = world.factions.get(aim.target_faction_id or "")
    is_target_gone = aim.target_faction_id is not None and (
        target is None or target.is_destroyed
    )
    is_expired = world.clock.turn - aim.chosen_turn >= scenario.tuning.ai.aim_max_turns
    return not (
        faction.leader_id != aim.leader_id
        or faction.stance.option_id != aim.stance_option_id
        or _holds_capital(world, faction_id) != aim.capital_held
        or is_target_gone
        or is_expired
    )


def _situation_score(
    world: WorldState,
    scenario: StrategyScenario,
    faction_id: FactionId,
    category: ScoreCategory,
) -> int:
    tuning = scenario.tuning.ai
    faction = world.factions[faction_id]
    is_poor = faction.treasury < tuning.low_treasury
    is_unstable = faction.stability < tuning.low_stability
    flags = {
        ScoreCategory.ATTACK: is_hostile(world, faction_id),
        ScoreCategory.ALLY: is_hostile(world, faction_id),
        ScoreCategory.HOARD: is_poor,
        ScoreCategory.BUILD: is_unstable,
    }
    return tuning.situation_bonus if flags.get(category, False) else 0


def _history_score(
    world: WorldState, faction_id: FactionId, category: ScoreCategory
) -> int:
    if category != ScoreCategory.ATTACK:
        return 0
    strengths = [
        item.strength for item in world.grounds if item.holder_faction_id == faction_id
    ]
    return min(max(strengths, default=0) // GROUND_HISTORY_DIVISOR, GROUND_HISTORY_CAP)


def _aim_scores(
    world: WorldState,
    scenario: StrategyScenario,
    faction_id: FactionId,
    leader: LeaderState,
) -> dict[ScoreCategory, int]:
    return {
        category: trait_score(world, scenario, faction_id, category)
        + stance_score(world, scenario, faction_id, category)
        + _situation_score(world, scenario, faction_id, category)
        + _history_score(world, faction_id, category)
        + temperament_bias(world.rng.seed, leader.id, category)
        for category in ScoreCategory
    }


def choose_aim(
    world: WorldState,
    scenario: StrategyScenario,
    faction_id: FactionId,
    rng: DeterministicRng,
) -> AimChoice | None:
    faction = world.factions[faction_id]
    if faction.leader_id is None or faction.leader_id not in world.leaders:
        return None
    target = pick_target(world, faction_id)
    scores = _aim_scores(world, scenario, faction_id, world.leaders[faction.leader_id])
    if target is None:
        scores.pop(ScoreCategory.ATTACK)
    category = _sample_category(scores, scenario.tuning.ai.variance_margin, rng)
    aim = AimState(
        category=category,
        target_faction_id=_aim_target(world, faction_id, category, target),
        chosen_turn=world.clock.turn,
        leader_id=faction.leader_id,
        stance_option_id=faction.stance.option_id,
        capital_held=_holds_capital(world, faction_id),
    )
    return AimChoice(aim, scores[category])


def _sample_category(
    scores: dict[ScoreCategory, int], margin: int, rng: DeterministicRng
) -> ScoreCategory:
    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0].value))
    floor = ranked[0][1] - margin
    near_best = [item for item in ranked if item[1] >= floor]
    weights = [score - floor + 1 for _, score in near_best]
    return rng.weighted_choice([category for category, _ in near_best], weights)


def refresh_aim(
    world: WorldState,
    scenario: StrategyScenario,
    faction_id: FactionId,
    rng: DeterministicRng,
) -> EventLogEntry | None:
    current = world.aims.get(faction_id)
    if current is not None and aim_is_valid(world, scenario, faction_id, current):
        return None
    choice = choose_aim(world, scenario, faction_id, rng)
    if choice is None:
        world.aims.pop(faction_id, None)
        return None
    world.aims[faction_id] = choice.aim
    subjects = [faction_id] + (
        [choice.aim.target_faction_id] if choice.aim.target_faction_id else []
    )
    cause = EventCause(
        summary_key=f"ai_aim_{choice.aim.category.value}",
        subject_ids=subjects,
        inputs={"score": choice.score},
    )
    return stamp_ai_event(world, AIM_SET_KIND, cause)
