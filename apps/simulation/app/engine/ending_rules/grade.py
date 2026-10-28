from typing import NamedTuple

from app.engine.ending_rules.hegemony import owned_region_percent
from app.engine.negotiation import player_faction_id
from app.engine.pressure.strain import compute_strain
from app.engine.pressure.wars import wars_of
from app.engine.pressure.will import compute_will
from app.engine.vassals.registry import vassalage_of
from app.models.world_state import WorldState
from strategy_contracts.endings import GRADE_ORDER, EndingGrade, EndingsTuning
from strategy_contracts.limits import FULL_SHARE_PERCENT
from strategy_contracts.scenario import StrategyScenario


class GradeReading(NamedTuple):
    grade: EndingGrade
    score: int
    inputs: dict[str, int]


def _clamp_percent(value: int) -> int:
    return max(0, min(FULL_SHARE_PERCENT, value))


def grade_components(world: WorldState, scenario: StrategyScenario) -> dict[str, int]:
    player_id = player_faction_id(world)
    faction = world.factions[player_id]
    has_war = bool(wars_of(world, player_id))
    will = compute_will(world, scenario, player_id).value
    strain = compute_strain(world, scenario, player_id).value
    scale = scenario.tuning.endings.treasury_scale
    return {
        "position": owned_region_percent(world),
        "stability": _clamp_percent(faction.stability),
        "treasury": _clamp_percent(faction.treasury * FULL_SHARE_PERCENT // scale),
        # NOTE: outside a war Will and Strain read 0; peace must not score as a broken will.
        "will": _clamp_percent(will) if has_war else FULL_SHARE_PERCENT,
        "strain": FULL_SHARE_PERCENT - _clamp_percent(strain),
    }


def weighted_score(components: dict[str, int], tuning: EndingsTuning) -> int:
    weighted = (
        components["position"] * tuning.weight_position
        + components["stability"] * tuning.weight_stability
        + components["treasury"] * tuning.weight_treasury
        + components["will"] * tuning.weight_will
        + components["strain"] * tuning.weight_strain
    )
    return weighted // FULL_SHARE_PERCENT


def tier_for_score(score: int, tuning: EndingsTuning) -> EndingGrade:
    tiers = (
        EndingGrade.RUIN,
        EndingGrade.BITTER,
        EndingGrade.HONORABLE,
        EndingGrade.TRIUMPH,
    )
    passed = sum(1 for threshold in tuning.grade_thresholds if score >= threshold)
    return tiers[passed]


def _is_pyrrhic(components: dict[str, int], tuning: EndingsTuning) -> bool:
    is_large = components["position"] >= tuning.pyrrhic_position_floor
    strain = FULL_SHARE_PERCENT - components["strain"]
    return is_large and strain >= tuning.pyrrhic_strain_floor


def _capped_for_vassal(grade: EndingGrade, tuning: EndingsTuning) -> EndingGrade:
    if GRADE_ORDER.index(grade) < GRADE_ORDER.index(tuning.vassal_best_grade):
        return tuning.vassal_best_grade
    return grade


def compute_grade(world: WorldState, scenario: StrategyScenario) -> GradeReading:
    tuning = scenario.tuning.endings
    components = grade_components(world, scenario)
    score = weighted_score(components, tuning)
    grade = tier_for_score(score, tuning)
    if _is_pyrrhic(components, tuning):
        grade = EndingGrade.PYRRHIC
    is_vassal = vassalage_of(world, player_faction_id(world)) is not None
    if is_vassal and tuning.toggles.is_vassal_outcome_enabled:
        grade = _capped_for_vassal(grade, tuning)
    return GradeReading(grade=grade, score=score, inputs=components)
