from uuid import UUID

from app.engine import negotiation
from app.engine.negotiation_memory import (
    PACT_SIGNED,
    TALKS_BROKEN_OFF,
    TALKS_REFUSED,
)
from app.engine.pressure.wars import find_war, side_score
from app.models.world_character import LeaderState, MemoryState
from app.models.world_events import PendingNegotiation
from app.models.world_state import WorldState
from app.services.scene_package_validation import require_valid_package
from app.services.trait_notes import trait_notes
from strategy_contracts.negotiation_rules import PEACE_TERM_KINDS
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.scene import (
    HiddenLimits,
    Participant,
    ParticipantKind,
    SceneInitiator,
    ScenePackage,
    SceneSituation,
    SceneType,
    SituationFact,
    TermsCardOutcome,
    TermsCardSpec,
    TermsResult,
)
from strategy_contracts.terms import TermKind

OPINION_WARM = 20
OPINION_COLD = -20
MOOD_WARM = "warm"
MOOD_GUARDED = "guarded"
MOOD_HOSTILE = "hostile"
MEMORY_TEMPLATES = {
    PACT_SIGNED: "You sealed a non-aggression pact with {subject} {when}.",
    TALKS_REFUSED: "You refused {subject}'s request for a pact {when}.",
    TALKS_BROKEN_OFF: "You broke off talks with {subject} {when}.",
}


def _mood(opinion: int) -> str:
    if opinion >= OPINION_WARM:
        return MOOD_WARM
    if opinion <= OPINION_COLD:
        return MOOD_HOSTILE
    return MOOD_GUARDED


def _grievances(leader: LeaderState, target_id: str | None) -> list[str]:
    opinion = leader.opinions.get(target_id) if target_id is not None else None
    if opinion is None:
        return []
    return [reason.cause for reason in opinion.reasons if reason.value < 0]


def _when(turns_ago: int) -> str:
    if turns_ago <= 0:
        return "this turn"
    if turns_ago == 1:
        return "1 turn ago"
    return f"{turns_ago} turns ago"


def _memory_note(world: WorldState, memory: MemoryState) -> str:
    subject = world.leaders.get(memory.subject_id or "")
    template = MEMORY_TEMPLATES.get(memory.kind, memory.kind)
    return template.format(
        subject=subject.name if subject else "a rival",
        when=_when(world.clock.turn - memory.turn),
    )


def _memory_notes(world: WorldState, leader: LeaderState) -> list[str]:
    recent_first = sorted(leader.memories, key=lambda item: (-item.turn, item.kind))
    return [_memory_note(world, memory) for memory in recent_first]


def _participant(
    world: WorldState, leader: LeaderState, scenario: StrategyScenario, opinion: int
) -> Participant:
    ambitions = {item.id: item.name for item in scenario.ambitions}
    return Participant(
        participant_id=leader.id,
        kind=ParticipantKind.LEADER,
        name=leader.name,
        trait_ids=list(leader.trait_ids),
        trait_notes=trait_notes(leader.trait_ids, scenario),
        goals=[ambitions.get(item, item) for item in leader.ambition_ids],
        mood=_mood(opinion),
        memory_notes=_memory_notes(world, leader),
    )


def _summary(
    world: WorldState, leader: LeaderState, pending: PendingNegotiation | None
) -> str:
    if pending is not None and pending.overture is not None:
        return _approach_summary(world, leader, pending)
    if pending is not None:
        return f"{leader.name} approaches {world.ruler.name} with an offer of a non-aggression pact."
    return f"{world.ruler.name} seeks a non-aggression pact with {leader.name}."


def _approach_summary(
    world: WorldState, leader: LeaderState, pending: PendingNegotiation
) -> str:
    assert pending.overture is not None
    return f"{leader.name} approaches {world.ruler.name}: {pending.overture.pretext}"


def _peace_summary(
    world: WorldState, leader: LeaderState, pending: PendingNegotiation | None
) -> str:
    if pending is not None and pending.overture is not None:
        return _approach_summary(world, leader, pending)
    return f"{world.ruler.name} sues for peace with {leader.name}."


def build_negotiation_package(
    world: WorldState,
    scenario: StrategyScenario,
    scene_id: UUID,
    counterpart_faction_id: str,
    pending: PendingNegotiation | None = None,
) -> ScenePackage:
    player = next(key for key, item in world.factions.items() if item.is_player)
    player_leader_id = world.factions[player].leader_id
    leader = world.leaders[world.factions[counterpart_faction_id].leader_id]
    opinion = negotiation.opinion_of(leader, player_leader_id)
    limits = negotiation.acceptance_range(
        world, scenario, player, counterpart_faction_id
    )
    rules = scenario.negotiation
    package = ScenePackage(
        scene_id=scene_id,
        initiator=SceneInitiator.PLAYER if pending is None else SceneInitiator.AI,
        is_declinable=pending is None or pending.is_declinable,
        playthrough_id=world.playthrough_id,
        scene_type=SceneType.NEGOTIATION,
        turn=world.clock.turn,
        situation=SceneSituation(
            summary=_summary(world, leader, pending),
            facts=[
                SituationFact(
                    label="Longest pact",
                    value=f"{rules.max_pact_turns} turns",
                )
            ],
        ),
        participants=[_participant(world, leader, scenario, opinion)],
        hidden_limits=HiddenLimits(
            acceptance=limits, real_grievances=_grievances(leader, player_leader_id)
        ),
        allowed_outcomes=[
            TermsCardSpec(
                allowed_term_kinds=list(rules.allowed_term_kinds),
                price_by_term_kind={TermKind.NON_AGGRESSION: rules.pact_value_per_turn},
                max_duration_turns=rules.max_pact_turns,
            )
        ],
        exchange_cap=negotiation.NEGOTIATION_EXCHANGE_CAP,
        default_outcome=TermsCardOutcome(result=TermsResult.REFUSED),
    )
    return require_valid_package(package)


def build_peace_package(
    world: WorldState,
    scenario: StrategyScenario,
    scene_id: UUID,
    counterpart_faction_id: str,
    pending: PendingNegotiation | None = None,
) -> ScenePackage:
    player = next(key for key, item in world.factions.items() if item.is_player)
    leader = world.leaders[world.factions[counterpart_faction_id].leader_id]
    war = find_war(world, player, counterpart_faction_id)
    opinion = negotiation.opinion_of(leader, world.factions[player].leader_id)
    limits = negotiation.acceptance_range(
        world, scenario, player, counterpart_faction_id
    )
    package = ScenePackage(
        scene_id=scene_id,
        initiator=SceneInitiator.PLAYER if pending is None else SceneInitiator.AI,
        is_declinable=pending is None or pending.is_declinable,
        playthrough_id=world.playthrough_id,
        scene_type=SceneType.PEACE,
        turn=world.clock.turn,
        situation=SceneSituation(
            summary=_peace_summary(world, leader, pending),
            facts=[
                SituationFact(
                    label="Your war score",
                    value=str(side_score(war, player) if war else 0),
                )
            ],
        ),
        participants=[_participant(world, leader, scenario, opinion)],
        hidden_limits=HiddenLimits(acceptance=limits),
        allowed_outcomes=[
            TermsCardSpec(
                allowed_term_kinds=list(PEACE_TERM_KINDS),
                price_by_term_kind={},
                war_score_available=side_score(war, player) if war else 0,
            )
        ],
        exchange_cap=negotiation.NEGOTIATION_EXCHANGE_CAP,
        default_outcome=TermsCardOutcome(result=TermsResult.REFUSED),
    )
    return require_valid_package(package)
