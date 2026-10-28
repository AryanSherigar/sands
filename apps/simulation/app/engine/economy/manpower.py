from app.engine.economy import events
from app.engine.economy.arithmetic import PERCENT, ceil_division, percent_of
from app.engine.economy.income import owned_regions
from app.engine.economy.state import EconomyRun
from app.engine.outrage.status import is_mobilized
from app.models.world_events import StateChange
from app.models.world_internal import uprising_for_region
from app.models.world_region import RegionState
from app.models.world_state import WorldState
from strategy_contracts.enums import ImprovementKind
from strategy_contracts.ids import FactionId, RegionId
from strategy_contracts.scenario import EconomyTuning

PER_THOUSAND = 1000


def faction_manpower(world: WorldState, faction_id: FactionId) -> int:
    return sum(region.manpower for region in owned_regions(world, faction_id))


def manpower_cap(region: RegionState, tuning: EconomyTuning) -> int:
    return percent_of(region.population, tuning.manpower_cap_percent)


def manpower_room(region: RegionState, tuning: EconomyTuning) -> int:
    return max(0, manpower_cap(region, tuning) - region.manpower)


def has_barracks(region: RegionState) -> bool:
    return any(
        improvement.kind is ImprovementKind.BARRACKS
        and improvement.turns_remaining == 0
        for improvement in region.improvements
    )


def region_refill(region: RegionState, tuning: EconomyTuning) -> int:
    if region.occupation is not None:
        return 0
    base = ceil_division(
        region.population * tuning.manpower_refill_per_thousand, PER_THOUSAND
    )
    if has_barracks(region):
        base = base * (PERCENT + tuning.barracks_refill_bonus_percent) // PERCENT
    return min(base, manpower_room(region, tuning))


def _mobilized_gain(
    run: EconomyRun, faction_id: FactionId, region: RegionState, gain: int
) -> int:
    if not is_mobilized(run.world, faction_id):
        return gain
    bonus = run.tuning.mobilization_manpower_bonus_percent
    boosted = gain * (PERCENT + bonus) // PERCENT
    return min(boosted, manpower_room(region, run.tuning))


def refill_manpower(run: EconomyRun, faction_id: FactionId) -> None:
    gains: dict[RegionId, int] = {}
    changes: list[StateChange] = []
    for region in owned_regions(run.world, faction_id):
        gain = region_refill(region, run.tuning)
        uprising = uprising_for_region(run.world.uprisings, region.id)
        if uprising is not None:
            gain = gain * (PERCENT - uprising.manpower_penalty_percent) // PERCENT
        gain = _mobilized_gain(run, faction_id, region, gain)
        if gain == 0:
            continue
        changes.append(
            StateChange(
                path=f"regions.{region.id}.manpower",
                before=region.manpower,
                after=region.manpower + gain,
            )
        )
        region.manpower += gain
        gains[region.id] = gain
    if gains:
        run.events.append(events.manpower_refilled(faction_id, gains, changes))
