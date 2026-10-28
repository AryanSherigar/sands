import hashlib
from dataclasses import dataclass

from app.engine.battles.deception import false_hint, has_deception, preparation_hint
from app.engine.battles.state import PERCENT, troop_count
from app.engine.economy.arithmetic import clamp
from app.engine.rng import DeterministicRng, derive_rng
from app.exceptions.base import SimulationServiceError
from app.models.base import WorldModel
from app.models.battle_intelligence import (
    Confidence,
    MissionTarget,
    ReconReport,
    ScoutCapture,
    ScoutMission,
    StrengthInterval,
)
from app.models.world_battle import BattleContingent, BattleState
from app.models.world_state import WorldState
from strategy_contracts.battle import BattleTuning
from strategy_contracts.enums import TroopType
from strategy_contracts.scenario import StrategyScenario

IDENTITY_DIGEST_LENGTH = 24


class ReconResolution(WorldModel):
    mission: ScoutMission
    report: ReconReport | None = None
    capture: ScoutCapture | None = None
    has_consumed_deception: bool = False


def intelligence_id(kind: str, *keys: str) -> str:
    encoded = "".join(f"{len(key)}:{key}" for key in keys).encode()
    return f"{kind}_{hashlib.sha256(encoded).hexdigest()[:IDENTITY_DIGEST_LENGTH]}"


def professional_rating(contingent: BattleContingent, tuning: BattleTuning) -> int:
    rating = tuning.faction_recon_ratings.get(
        contingent.faction_id, tuning.professional_recon_rating
    )
    return max(0, rating - contingent.recon_penalty)


def contact_strength(total: int) -> StrengthInterval:
    return StrengthInterval(minimum=0, maximum=1 << total.bit_length())


def estimate_strength(
    total: int, width: int, center_shift: int = 0
) -> StrengthInterval:
    center = max(0, total * (PERCENT + center_shift) // PERCENT)
    return StrengthInterval(
        minimum=max(0, center * (PERCENT - width) // PERCENT),
        maximum=(center * (PERCENT + width) + PERCENT - 1) // PERCENT,
    )


def _mission_participants(
    world: WorldState, mission: ScoutMission
) -> tuple[BattleState, BattleContingent, BattleContingent]:
    battle = next(
        (battle for battle in world.battles if battle.id == mission.battle_id), None
    )
    if battle is None:
        raise SimulationServiceError("mission requires an opposing contingent")
    observer = battle.contingents.get(mission.observer_faction_id)
    subject = battle.contingents.get(mission.subject_faction_id)
    if observer is None or subject is None or observer.side == subject.side:
        raise SimulationServiceError("mission requires an opposing contingent")
    if (
        mission.is_resolved
        or mission.execution_turn != world.clock.turn
        or mission.execution_wave != battle.exchanges_used + 1
    ):
        raise SimulationServiceError("mission execution boundary is unavailable")
    return battle, observer, subject


def _capture(
    world: WorldState, battle: BattleState, mission: ScoutMission, tuning: BattleTuning
) -> ScoutCapture:
    return ScoutCapture(
        id=intelligence_id("scout_capture", battle.id, mission.id),
        battle_id=battle.id,
        mission_id=mission.id,
        captor_faction_id=mission.subject_faction_id,
        origin_faction_id=mission.observer_faction_id,
        captured_turn=world.clock.turn,
        captured_exchange=battle.total_exchanges + 1,
        expires_turn=world.clock.turn + tuning.scout_detention_turns,
        mission_target=mission.target,
        briefing_hint=mission.briefing_hint,
        recon_penalty=tuning.capture_recon_penalty,
    )


@dataclass(frozen=True)
class EstimateAccuracy:
    width: int
    shift: int
    is_useful: bool
    is_deceived: bool


def _accuracy(
    tuning: BattleTuning, rng: DeterministicRng, is_useful: bool, is_deceived: bool
) -> EstimateAccuracy:
    width = (
        tuning.useful_estimate_width_percent
        if is_useful
        else tuning.uncertain_estimate_width_percent
    )
    shift = (
        0
        if is_useful
        else rng.roll_range(
            -tuning.uncertain_center_error_percent,
            tuning.uncertain_center_error_percent,
        )
    )
    shift += tuning.deception_center_shift_percent if is_deceived else 0
    return EstimateAccuracy(width, shift, is_useful, is_deceived)


def _base_report(
    world: WorldState,
    battle: BattleState,
    mission: ScoutMission,
    subject: BattleContingent,
    accuracy: EstimateAccuracy,
) -> ReconReport:
    return ReconReport(
        id=intelligence_id("recon_report", battle.id, mission.id),
        battle_id=battle.id,
        observer_faction_id=mission.observer_faction_id,
        subject_faction_id=subject.faction_id,
        mission_id=mission.id,
        target=mission.target,
        observed_turn=world.clock.turn,
        observed_exchange=battle.total_exchanges + 1,
        available_from_wave=mission.execution_wave + 1,
        strength=estimate_strength(
            troop_count(world, subject), accuracy.width, accuracy.shift
        ),
        confidence=Confidence.HIGH if accuracy.is_useful else Confidence.LOW,
    )


def _composition(world: WorldState, subject: BattleContingent) -> dict[TroopType, int]:
    composition = {
        troop_type: sum(
            world.armies[identity].troops.get(troop_type, 0)
            for identity in subject.army_ids
            if identity in world.armies
        )
        for troop_type in TroopType
    }
    return {troop_type: count for troop_type, count in composition.items() if count}


def _target_observation(
    world: WorldState,
    subject: BattleContingent,
    accuracy: EstimateAccuracy,
    report: ReconReport,
) -> None:
    if (
        report.target == MissionTarget.COMPOSITION
        and accuracy.is_useful
        and not accuracy.is_deceived
    ):
        report.composition = _composition(world, subject)
    if report.target == MissionTarget.RESERVES:
        reserves = sum(
            sum(deployment.reserve.values())
            for deployment in subject.deployments.values()
        )
        report.reserves = estimate_strength(reserves, accuracy.width, accuracy.shift)
    if report.target == MissionTarget.PREPARATION:
        hint = preparation_hint(subject)
        report.preparation_hint = (
            false_hint(hint) if accuracy.is_deceived or not accuracy.is_useful else hint
        )


def _mission_probabilities(
    battle: BattleState,
    observer: BattleContingent,
    subject: BattleContingent,
    tuning: BattleTuning,
) -> tuple[int, int]:
    own_rating = professional_rating(observer, tuning)
    enemy_rating = professional_rating(subject, tuning)
    capture = clamp(
        tuning.capture_base_percent
        + (enemy_rating - own_rating) // tuning.capture_rating_divisor,
        tuning.capture_min_percent,
        tuning.capture_max_percent,
    )
    score = (
        tuning.recon_base_percent
        + (own_rating - enemy_rating) // tuning.recon_rating_divisor
        - tuning.terrain_concealment[battle.terrain]
    )
    if has_deception(battle, subject):
        score -= tuning.deception_penalty
    return capture, clamp(score, tuning.recon_min_percent, tuning.recon_max_percent)


def resolve_recon(
    world: WorldState, mission: ScoutMission, scenario: StrategyScenario
) -> ReconResolution:
    """Observe a frozen boundary without altering troops, penalties or records."""
    battle, observer, subject = _mission_participants(world, mission)
    tuning = scenario.tuning.battle
    rng = _mission_rng(world, battle, mission)
    capture_chance, success_chance = _mission_probabilities(
        battle, observer, subject, tuning
    )
    resolved = mission.model_copy(update={"is_resolved": True}, deep=True)
    result = ReconResolution(
        mission=resolved, has_consumed_deception=has_deception(battle, subject)
    )
    if rng.roll(PERCENT) < capture_chance:
        result.capture = _capture(world, battle, mission, tuning)
        return result
    is_useful = rng.roll(PERCENT) < success_chance
    accuracy = _accuracy(tuning, rng, is_useful, result.has_consumed_deception)
    result.report = _base_report(world, battle, mission, subject, accuracy)
    _target_observation(world, subject, accuracy, result.report)
    return result


def _mission_rng(
    world: WorldState, battle: BattleState, mission: ScoutMission
) -> DeterministicRng:
    return derive_rng(
        world.rng.seed,
        world.clock.turn,
        "battle_recon",
        battle.id,
        battle.total_exchanges + 1,
        mission.observer_faction_id,
        mission.id,
    )
