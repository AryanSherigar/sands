from uuid import UUID

from app.models.world_character import (
    GovernorState,
    LeaderState,
    OpinionReason,
    OpinionState,
)
from app.models.world_diplomacy import PrisonerKind, PrisonerState
from app.models.world_events import (
    EventCause,
    EventLogEntry,
    PendingJudgment,
    PhaseName,
    StateChange,
)
from app.models.world_peace import HostageState
from app.models.world_state import WorldState
from strategy_contracts.examples import load_three_crowns
from strategy_contracts.judgment import JudgmentSubjectKind, JudgmentTuning
from strategy_contracts.scenario import StrategyScenario

from tests.models.builders import make_region, make_world

PLAYER = "house_carrow"
RIVAL = "house_ashford"
PLAYER_LEADER = "valdren"
RIVAL_LEADER = "mira"
CAPTIVE_ID = "captive_1"
CAPTIVE_CHARACTER = "ser_orrin"
GOVERNOR_ID = "harl"
OTHER_GOVERNOR_ID = "alden"
GOVERNOR_REGION = "ash_ford"
OTHER_REGION = "high_cairn"
TURN = 5
SCENE_ID = UUID(int=7)


def judgment_world(turn: int = TURN) -> WorldState:
    world = make_world()
    world.clock.turn = turn
    world.coalition_ruleset = 1
    world.leaders = {
        PLAYER_LEADER: LeaderState(
            id=PLAYER_LEADER, name="Valdren", faction_id=PLAYER, age=40
        ),
        RIVAL_LEADER: LeaderState(
            id=RIVAL_LEADER, name="Mira", faction_id=RIVAL, age=40
        ),
    }
    world.factions[PLAYER].leader_id = PLAYER_LEADER
    world.factions[RIVAL].leader_id = RIVAL_LEADER
    world.leaders[RIVAL_LEADER].opinions[PLAYER_LEADER] = OpinionState(
        target_id=PLAYER_LEADER,
        reasons=[OpinionReason(cause="test", value=0, fade_per_turn=0)],
    )
    world.prisoners = [captive()]
    for region_id in (GOVERNOR_REGION, OTHER_REGION):
        world.regions[region_id] = make_region(region_id, PLAYER)
    world.governors = {
        GOVERNOR_ID: governor(GOVERNOR_ID, GOVERNOR_REGION, -30),
        OTHER_GOVERNOR_ID: governor(OTHER_GOVERNOR_ID, OTHER_REGION, 10),
    }
    world.regions[GOVERNOR_REGION].governor_id = GOVERNOR_ID
    world.regions[OTHER_REGION].governor_id = OTHER_GOVERNOR_ID
    return world


def captive() -> PrisonerState:
    return PrisonerState(
        id=CAPTIVE_ID,
        held_by_id=PLAYER,
        origin_faction_id=RIVAL,
        kind=PrisonerKind.CHARACTER,
        character_id=CAPTIVE_CHARACTER,
    )


def governor(governor_id: str, region_id: str, opinion: int) -> GovernorState:
    return GovernorState(
        id=governor_id,
        name=governor_id.title(),
        region_id=region_id,
        opinion_of_ruler=opinion,
    )


def judgment_scenario(is_enabled: bool = True) -> StrategyScenario:
    scenario = load_three_crowns()
    scenario.tuning.judgments = JudgmentTuning(is_enabled=is_enabled)
    return scenario


def captive_pending() -> PendingJudgment:
    return PendingJudgment(
        subject_kind=JudgmentSubjectKind.CAPTIVE,
        subject_id=CAPTIVE_ID,
        accused_faction_id=RIVAL,
        trigger_event="battle_surrender",
        cooldown_until_turn=TURN + 6,
    )


def governor_pending() -> PendingJudgment:
    return PendingJudgment(
        subject_kind=JudgmentSubjectKind.GOVERNOR,
        subject_id=GOVERNOR_ID,
        accused_faction_id=PLAYER,
        trigger_event="uprising_crushed",
        cooldown_until_turn=TURN + 6,
    )


def arm_manually(world: WorldState, pending: PendingJudgment) -> UUID:
    world.progress.pending_scene_id = SCENE_ID
    world.progress.pending_judgment = pending
    world.progress.negotiation_counterpart_id = pending.accused_faction_id
    return SCENE_ID


def uprising_event(
    kind: str,
    region_id: str = GOVERNOR_REGION,
    faction_id: str = PLAYER,
    stage_after: str | None = None,
) -> EventLogEntry:
    changes = (
        [StateChange(path="uprisings.u1.stage", before="riot", after=stage_after)]
        if stage_after is not None
        else []
    )
    return EventLogEntry(
        seq=1,
        turn=TURN,
        phase=PhaseName.INTERNAL,
        kind=kind,
        cause=EventCause(
            summary_key=f"internal.{kind}", subject_ids=["u1", faction_id, region_id]
        ),
        changes=changes,
    )


def mercy_hostage(is_at_mercy: bool = True) -> HostageState:
    return HostageState(
        id="hostage_1",
        giver_id=RIVAL,
        holder_id=PLAYER,
        leader_id=RIVAL_LEADER,
        release_turn=TURN + 10,
        truce_id="truce_1",
        is_at_mercy=is_at_mercy,
    )
