from dataclasses import dataclass

from app.engine.economy import events
from app.engine.economy.arithmetic import PERCENT
from app.engine.economy.ledger import change_treasury
from app.engine.economy.state import EconomyRun
from app.engine.outrage.status import is_mobilized
from app.models.world_internal import uprising_for_region
from app.models.world_region import RegionState
from app.models.world_state import WorldState
from strategy_contracts.ids import FactionId, RegionId
from strategy_contracts.scenario import EconomyTuning


@dataclass(frozen=True)
class IncomeReport:
    tax_percent: int
    by_region: dict[RegionId, int]
    occupied_region_ids: tuple[RegionId, ...]

    @property
    def total(self) -> int:
        return sum(self.by_region.values())


def owned_regions(world: WorldState, faction_id: FactionId) -> list[RegionState]:
    return [
        region
        for _, region in sorted(world.regions.items())
        if region.owner_id == faction_id
    ]


def region_income(region: RegionState, tax_percent: int) -> int:
    if region.occupation is not None:
        return 0
    return (
        region.wealth * tax_percent * (PERCENT - region.unrest) // (PERCENT * PERCENT)
    )


def faction_income(
    world: WorldState, tuning: EconomyTuning, faction_id: FactionId
) -> IncomeReport:
    tax_percent = tuning.tax_rate_percent[world.factions[faction_id].tax_rate]
    if is_mobilized(world, faction_id):
        tax_percent += tuning.mobilization_tax_bonus_percent
    regions = owned_regions(world, faction_id)
    return IncomeReport(
        tax_percent=tax_percent,
        by_region={
            region.id: _uprising_income(world, region, tax_percent)
            for region in regions
            if region.occupation is None
        },
        occupied_region_ids=tuple(
            region.id for region in regions if region.occupation is not None
        ),
    )


def _uprising_income(world: WorldState, region: RegionState, tax_percent: int) -> int:
    income = region_income(region, tax_percent)
    uprising = uprising_for_region(world.uprisings, region.id)
    if uprising is None:
        return income
    return income * (PERCENT - uprising.income_penalty_percent) // PERCENT


def collect_income(run: EconomyRun, faction_id: FactionId) -> IncomeReport:
    report = faction_income(run.world, run.tuning, faction_id)
    if report.by_region or report.occupied_region_ids:
        change = change_treasury(run.world.factions[faction_id], report.total)
        run.events.append(
            events.income_collected(
                faction_id,
                report.tax_percent,
                report.by_region,
                report.occupied_region_ids,
                change,
            )
        )
    return report
