import hashlib
from collections.abc import Callable
from dataclasses import dataclass, field
from uuid import UUID

from app.engine.campaign import advance_campaign, begin_campaign
from app.engine.hashing import world_hash
from app.engine.pipeline import TurnResult
from app.engine.stances.cadence import STANCE_INTERVAL_TURNS
from app.engine.stances.fallback import fallback_stance_id
from app.engine.stances.menu import resolve_stance_menu
from app.engine.world_init import new_world
from app.models.world_events import EventLogEntry, TurnStatus
from app.models.world_faction import StanceState
from app.models.world_player import PlayerRuler
from app.models.world_state import WorldState
from strategy_contracts.scenario import FactionSetup, StrategyScenario

HEADLESS_PLAYTHROUGH_ID = UUID("00000000-0000-0000-0000-00000000a1a1")
MAX_WAVE_ADVANCES = 16
SNOWBALL_REGION_PERCENT = 80
BANKRUPT_TURNS = 8
UNREST_COLLAPSE_TURNS = 8
COLLAPSED_STABILITY = 5
ENDLESS_WAR_TURNS = 40
STAGNANT_TURNS = 10
PLANNED_KIND = "ai_order_planned"
NEUTRAL_OWNER = "neutral"
OBSERVER_FACTION_ID = "observer"
OBSERVER_COLOR = "#808080"
OBSERVER_TREASURY = 1_000_000
FLAG_SNOWBALL = "snowball"
FLAG_BANKRUPTCY = "bankruptcy_spiral"
FLAG_ENDLESS_WAR = "endless_war"
FLAG_UNREST = "unrest_collapse"
FLAG_STAGNATION = "stagnation"
FLAG_PAUSED = "paused"


@dataclass(frozen=True)
class TurnSample:
    turn: int
    regions_by_owner: dict[str, int]
    treasury_by_faction: dict[str, int]
    stability_by_faction: dict[str, int]
    war_count: int
    planned_orders: int


@dataclass(frozen=True)
class HeadlessReport:
    seed: int
    turns_run: int
    samples: list[TurnSample]
    flags: list[str]
    final_hash: str
    order_fingerprints: dict[str, str] = field(default_factory=dict)
    final_world: WorldState | None = None


def observer_scenario(scenario: StrategyScenario) -> StrategyScenario:
    """Add an inert, wealthy player faction so every real faction is AI-driven."""
    observed = scenario.model_copy(deep=True)
    observed.factions.append(
        FactionSetup(
            id=OBSERVER_FACTION_ID,
            name="Observer",
            color=OBSERVER_COLOR,
            treasury=OBSERVER_TREASURY,
            is_playable=True,
        )
    )
    # NOTE: the observer's wealth would read as hegemony and end every game.
    observed.tuning.endings.toggles.is_hegemony_enabled = False
    return observed


def start_headless_world(
    scenario: StrategyScenario, seed: int, ruler: PlayerRuler
) -> WorldState:
    return new_world(
        observer_scenario(scenario),
        HEADLESS_PLAYTHROUGH_ID,
        seed,
        OBSERVER_FACTION_ID,
        ruler,
    )


def _apply_fallback_stances(world: WorldState, scenario: StrategyScenario) -> None:
    for faction_id, faction in sorted(world.factions.items()):
        leader = world.leaders.get(faction.leader_id or "")
        if faction.is_destroyed or leader is None:
            continue
        stance = faction.stance
        is_due = stance.option_id is None or (
            world.clock.turn - stance.chosen_turn >= STANCE_INTERVAL_TURNS
        )
        menu = resolve_stance_menu(scenario, faction_id)
        if is_due and menu:
            faction.stance = StanceState(
                option_id=fallback_stance_id(leader, menu, scenario),
                chosen_turn=world.clock.turn,
            )


def _play_turn(world: WorldState, scenario: StrategyScenario) -> TurnResult:
    result = begin_campaign(world, scenario)
    advances = 0
    while (
        result.status is TurnStatus.AWAITING_COMMANDS and advances < MAX_WAVE_ADVANCES
    ):
        current = result.world
        waves = advance_campaign(
            current,
            scenario,
            expected_turn=current.clock.turn,
            expected_wave=current.progress.completed_waves + 1,
        )
        events = result.events + waves.result.events
        result = waves.result
        result.events = events
        advances += 1
    return result


def _sample(world: WorldState, planned: int) -> TurnSample:
    regions: dict[str, int] = {}
    for region in world.regions.values():
        owner = region.owner_id or NEUTRAL_OWNER
        regions[owner] = regions.get(owner, 0) + 1
    return TurnSample(
        turn=world.clock.turn,
        regions_by_owner=dict(sorted(regions.items())),
        treasury_by_faction={
            faction_id: faction.treasury
            for faction_id, faction in sorted(world.factions.items())
        },
        stability_by_faction={
            faction_id: faction.stability
            for faction_id, faction in sorted(world.factions.items())
        },
        war_count=len(world.wars),
        planned_orders=planned,
    )


def _planned(events: list[EventLogEntry]) -> list[EventLogEntry]:
    return [event for event in events if event.kind == PLANNED_KIND]


def _fingerprints(planned: list[EventLogEntry]) -> dict[str, str]:
    lines: dict[str, list[str]] = {}
    for event in planned:
        faction_id = event.cause.subject_ids[0]
        lines.setdefault(faction_id, []).append(
            f"{event.turn}:{event.cause.summary_key}:{sorted(event.cause.inputs.items())}"
        )
    return {
        faction_id: hashlib.sha256("|".join(items).encode()).hexdigest()
        for faction_id, items in sorted(lines.items())
    }


def _is_snowball(sample: TurnSample) -> bool:
    total = sum(sample.regions_by_owner.values())
    return any(
        count * 100 >= total * SNOWBALL_REGION_PERCENT
        for owner, count in sample.regions_by_owner.items()
        if owner not in (NEUTRAL_OWNER, OBSERVER_FACTION_ID)
    )


def _has_streak(
    samples: list[TurnSample], is_bad: Callable[[TurnSample, str], bool], length: int
) -> bool:
    factions = [
        faction_id
        for faction_id in (samples[0].treasury_by_faction if samples else [])
        if faction_id != OBSERVER_FACTION_ID
    ]
    for faction_id in factions:
        streak = 0
        for sample in samples:
            streak = streak + 1 if is_bad(sample, faction_id) else 0
            if streak >= length:
                return True
    return False


def _has_bankruptcy_spiral(samples: list[TurnSample]) -> bool:
    return _has_streak(
        samples,
        lambda sample, faction_id: sample.treasury_by_faction[faction_id] <= 0,
        BANKRUPT_TURNS,
    )


def _has_unrest_collapse(samples: list[TurnSample]) -> bool:
    return _has_streak(
        samples,
        lambda sample, faction_id: (
            sample.stability_by_faction[faction_id] <= COLLAPSED_STABILITY
        ),
        UNREST_COLLAPSE_TURNS,
    )


def _is_stagnant(samples: list[TurnSample]) -> bool:
    recent = samples[-STAGNANT_TURNS:]
    return len(recent) == STAGNANT_TURNS and all(s.planned_orders == 0 for s in recent)


def _has_endless_war(world: WorldState) -> bool:
    return any(
        world.clock.turn - war.started_turn >= ENDLESS_WAR_TURNS for war in world.wars
    )


def run_headless(
    scenario: StrategyScenario,
    seed: int,
    turns: int,
    ruler: PlayerRuler,
) -> HeadlessReport:
    scenario = observer_scenario(scenario)
    world = start_headless_world(scenario, seed, ruler)
    samples: list[TurnSample] = []
    planned_events: list[EventLogEntry] = []
    flags: list[str] = []
    for _ in range(turns):
        _apply_fallback_stances(world, scenario)
        result = _play_turn(world, scenario)
        world = result.world
        planned = _planned(result.events)
        planned_events.extend(planned)
        samples.append(_sample(world, len(planned)))
        if result.status is not TurnStatus.RESOLVED:
            flags.append(FLAG_PAUSED)
            break
        if world.ending is not None:
            break
    flags.extend(detect_flags(world, samples))
    return HeadlessReport(
        seed=seed,
        turns_run=len(samples),
        samples=samples,
        flags=sorted(set(flags)),
        final_hash=world_hash(world),
        order_fingerprints=_fingerprints(planned_events),
        final_world=world,
    )


def detect_flags(world: WorldState, samples: list[TurnSample]) -> list[str]:
    flags: list[str] = []
    if samples and _is_snowball(samples[-1]):
        flags.append(FLAG_SNOWBALL)
    if _has_bankruptcy_spiral(samples):
        flags.append(FLAG_BANKRUPTCY)
    if _has_unrest_collapse(samples):
        flags.append(FLAG_UNREST)
    if _is_stagnant(samples):
        flags.append(FLAG_STAGNATION)
    if _has_endless_war(world):
        flags.append(FLAG_ENDLESS_WAR)
    return flags
