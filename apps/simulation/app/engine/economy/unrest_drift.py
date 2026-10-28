from app.engine.economy import events
from app.engine.economy.arithmetic import PERCENT, clamp
from app.engine.economy.income import owned_regions
from app.engine.economy.state import EconomyRun
from app.models.world_events import StateChange
from strategy_contracts.ids import FactionId, RegionId


def drift_unrest(run: EconomyRun, faction_id: FactionId) -> None:
    faction = run.world.factions[faction_id]
    drift = run.tuning.tax_unrest_drift[faction.tax_rate]
    moved: dict[RegionId, int] = {}
    changes: list[StateChange] = []
    for region in owned_regions(run.world, faction_id):
        after = clamp(region.unrest + drift, 0, PERCENT)
        if region.occupation is not None or after == region.unrest:
            continue
        changes.append(
            StateChange(
                path=f"regions.{region.id}.unrest", before=region.unrest, after=after
            )
        )
        moved[region.id] = after - region.unrest
        region.unrest = after
    if moved:
        run.events.append(events.unrest_drifted(faction_id, drift, moved, changes))
