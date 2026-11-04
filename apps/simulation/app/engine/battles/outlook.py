from app.engine.battles.modifiers import (
    attack_pressure,
    average_protection,
    morale_factor_percent,
    protection_for_active,
    scale_attack_pressure,
    troop_attack,
)
from app.engine.battles.state import PERCENT
from app.engine.battles.views import observed_battle, project_battle
from app.models.battle_intelligence import Confidence, ReconReport, StrengthInterval
from app.models.world_battle import (
    BattleContingent,
    BattleOutlook,
    BattleSide,
    BattleState,
    LossEstimate,
    OpponentView,
    OutlookBasis,
    OutlookFactor,
    StandingPlan,
)
from app.models.world_state import WorldState
from strategy_contracts.battle import BattleTuning, SupplyState, Weather
from strategy_contracts.enums import TroopType
from strategy_contracts.scenario import StrategyScenario

CONFIDENCE_ORDER = (Confidence.LOW, Confidence.MEDIUM, Confidence.HIGH)


def _latest_scouted(reports: list[ReconReport]) -> ReconReport | None:
    return max(
        reports,
        key=lambda report: (report.observed_turn, report.observed_exchange, report.id),
        default=None,
    )


def _even_mix(total: int) -> dict[TroopType, int]:
    kinds = list(TroopType)
    share, remainder = divmod(total, len(kinds))
    return {
        kind: share + (1 if index < remainder else 0)
        for index, kind in enumerate(kinds)
    }


def _scaled_composition(
    composition: dict[TroopType, int], total: int
) -> dict[TroopType, int]:
    known = sum(composition.values())
    if not known:
        return _even_mix(total)
    return {kind: count * total // known for kind, count in composition.items()}


def _enemy_mix(
    opponents: list[OpponentView],
) -> tuple[StrengthInterval, dict[TroopType, int], OutlookBasis, Confidence]:
    minimum = maximum = 0
    composition: dict[TroopType, int] = {}
    has_full_composition = True
    confidence = Confidence.HIGH
    for opponent in opponents:
        minimum += opponent.strength.minimum
        maximum += opponent.strength.maximum
        report = _latest_scouted(opponent.reports)
        if report is None or report.composition is None:
            has_full_composition = False
        if report is None:
            confidence = Confidence.LOW
            continue
        for kind, count in (report.composition or {}).items():
            composition[kind] = composition.get(kind, 0) + count
        if CONFIDENCE_ORDER.index(report.confidence) < CONFIDENCE_ORDER.index(
            confidence
        ):
            confidence = report.confidence
    basis = (
        OutlookBasis.SCOUTED_COMPOSITION
        if has_full_composition and composition
        else OutlookBasis.ASSUMED_EVEN_MIX
    )
    return (
        StrengthInterval(minimum=minimum, maximum=maximum),
        composition,
        basis,
        confidence,
    )


def _enemy_pressure(
    battle: BattleState, active: dict[TroopType, int], tuning: BattleTuning
) -> int:
    stub = BattleContingent(
        faction_id="unseen", side=BattleSide.ATTACKER, army_ids=[], entry_troops=0
    )
    raw = sum(
        troop_attack(count, kind, battle, stub, tuning)
        for kind, count in active.items()
    )
    return scale_attack_pressure(
        raw,
        battle,
        StandingPlan(),
        SupplyState.SUPPLIED,
        morale_factor_percent(tuning, 0, 0),
        tuning,
    )


def _expected_losses(
    pressure: int, protection: int, damage_percent: int, tuning: BattleTuning
) -> int:
    numerator = pressure * tuning.casualty_rate_percent * damage_percent
    return numerator // (PERCENT * PERCENT * max(1, protection))


def _loss_range(
    pressure_low: int,
    pressure_mid: int,
    pressure_high: int,
    protection: int,
    cap: int,
    tuning: BattleTuning,
) -> LossEstimate:
    mid_percent = (
        tuning.random_damage_min_percent + tuning.random_damage_max_percent
    ) // 2
    low = _expected_losses(
        pressure_low, protection, tuning.random_damage_min_percent, tuning
    )
    expected = _expected_losses(pressure_mid, protection, mid_percent, tuning)
    high = _expected_losses(
        pressure_high, protection, tuning.random_damage_max_percent, tuning
    )
    return LossEstimate(
        low=min(low, cap), expected=min(expected, cap), high=min(high, cap)
    )


def _own_factors(
    battle: BattleState, contingent: BattleContingent, tuning: BattleTuning
) -> list[OutlookFactor]:
    return [
        OutlookFactor(
            id="formation",
            percent=tuning.formation_attack_percent[contingent.plan.formation],
        ),
        OutlookFactor(
            id="tactic", percent=tuning.tactic_attack_percent[contingent.plan.tactic]
        ),
        OutlookFactor(
            id="weather",
            percent=tuning.weather_attack_percent[battle.weather or Weather.CLEAR],
        ),
        OutlookFactor(
            id="supply",
            percent=tuning.supply_attack_percent[
                contingent.supply or SupplyState.SUPPLIED
            ],
        ),
    ]


def _active_total(contingent: BattleContingent) -> int:
    return sum(
        sum(deployment.active.values())
        for deployment in contingent.deployments.values()
    )


def _enemy_active_for(
    total: int, composition: dict[TroopType, int], basis: OutlookBasis
) -> dict[TroopType, int]:
    if basis == OutlookBasis.SCOUTED_COMPOSITION:
        return _scaled_composition(composition, total)
    return _even_mix(total)


def estimate_outlook(
    world: WorldState,
    battle_id: str,
    observer_faction_id: str,
    scenario: StrategyScenario,
) -> BattleOutlook | None:
    """Next-exchange expected losses for both sides from observer-visible facts only.

    The enemy's true morale, plan and supply are never read; they are held neutral.
    """
    battle = observed_battle(world, battle_id, observer_faction_id)
    own = battle.contingents[observer_faction_id]
    tuning = scenario.tuning.battle
    opponents = project_battle(
        world, battle_id, observer_faction_id, scenario
    ).opponents
    interval, composition, basis, confidence = _enemy_mix(opponents)
    if not interval.maximum or not _active_total(own):
        return None
    mid = (interval.minimum + interval.maximum) // 2
    pressures = [
        _enemy_pressure(battle, _enemy_active_for(total, composition, basis), tuning)
        for total in (interval.minimum, mid, interval.maximum)
    ]
    own_pressure = attack_pressure(world, battle, own, tuning)
    enemy_protection = protection_for_active(
        _enemy_active_for(mid, composition, basis), battle, StandingPlan(), tuning
    )
    return BattleOutlook(
        own_losses=_loss_range(
            *pressures,
            average_protection(battle, own, tuning),
            _active_total(own),
            tuning,
        ),
        enemy_losses=_loss_range(
            own_pressure,
            own_pressure,
            own_pressure,
            enemy_protection,
            interval.maximum,
            tuning,
        ),
        own_share_percent=PERCENT * own_pressure // max(1, own_pressure + pressures[1]),
        confidence=confidence,
        basis=basis,
        factors=_own_factors(battle, own, tuning),
    )
