"""War, map and stability metrics shared by the AI-only census scripts."""

import statistics
from dataclasses import dataclass, field

from app.engine.ai.headless import NEUTRAL_OWNER, OBSERVER_FACTION_ID, HeadlessReport
from app.engine.peace.signing import PEACE_SIGNED
from app.models.world_events import EventLogEntry
from app.models.world_state import WorldState

REGION_CONQUERED = "region_conquered"
STABILITY_CHECKPOINTS = (20, 60, 120)
LONG_WAR_TURNS = 50
PERCENT = 100


@dataclass
class WarLedger:
    started: dict[str, int] = field(default_factory=dict)
    agreed_lengths: list[int] = field(default_factory=list)
    other_lengths: list[int] = field(default_factory=list)
    regions_conquered: int = 0

    def observe(self, world: WorldState, events: list[EventLogEntry]) -> None:
        self.regions_conquered += sum(
            1 for event in events if event.kind == REGION_CONQUERED
        )
        is_peace_signed = any(event.kind == PEACE_SIGNED for event in events)
        live = {war.id: war.started_turn for war in world.wars}
        for war_id, started_turn in self.started.items():
            if war_id not in live:
                length = world.clock.turn - started_turn
                target = self.agreed_lengths if is_peace_signed else self.other_lengths
                target.append(length)
        self.started = live


def _median(values: list[int]) -> float:
    return statistics.median(values) if values else 0


def summarize_wars(ledger: WarLedger) -> str:
    lengths = ledger.agreed_lengths + ledger.other_lengths
    ended = len(lengths)
    agreed_percent = len(ledger.agreed_lengths) * PERCENT // ended if ended else 0
    long_count = sum(1 for length in lengths if length > LONG_WAR_TURNS)
    return (
        f"  wars ended {ended} (agreement {agreed_percent}%), "
        f"median length {_median(lengths)}, over {LONG_WAR_TURNS} turns: {long_count}, "
        f"still open {len(ledger.started)}, regions conquered {ledger.regions_conquered}"
    )


def summarize_stability(report: HeadlessReport) -> str:
    parts = []
    for sample in report.samples:
        if sample.turn not in STABILITY_CHECKPOINTS:
            continue
        values = [
            value
            for faction_id, value in sample.stability_by_faction.items()
            if faction_id != OBSERVER_FACTION_ID
        ]
        parts.append(
            f"t{sample.turn} min {min(values)} median {statistics.median(values)}"
        )
    return "  stability " + "; ".join(parts)


def summarize_map(report: HeadlessReport) -> str:
    last = report.samples[-1]
    owned = {
        owner: count
        for owner, count in last.regions_by_owner.items()
        if owner not in (NEUTRAL_OWNER, OBSERVER_FACTION_ID)
    }
    total = sum(last.regions_by_owner.values())
    largest_percent = max(owned.values()) * PERCENT // total if owned else 0
    destroyed = sum(
        1
        for faction in (
            report.final_world.factions.values() if report.final_world else []
        )
        if faction.is_destroyed
    )
    return f"  houses destroyed {destroyed}, largest region share {largest_percent}%"
