from uuid import UUID

from app.engine import negotiation
from app.engine.negotiation_memory import (
    PACT_SIGNED,
    TALKS_BROKEN_OFF,
    TALKS_REFUSED,
)
from app.engine.pressure.wars import find_war, side_score
from app.engine.succession.opinions import INHERITED_PREFIX
from app.models.world_character import LeaderState, MemoryState
from app.models.world_events import PendingNegotiation
from app.models.world_state import WorldState
from app.services.peace_brief import build_peace_brief
from app.services.scene_grudges import build_grudges
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

UNPRICED = 0
PEACETIME_CLAUSE_KINDS = (
    TermKind.NON_AGGRESSION,
    TermKind.TRADE_DEAL,
    TermKind.MILITARY_ACCESS,
    TermKind.PAY_GOLD,
    TermKind.TRIBUTE,
    TermKind.CEDE_REGION,
    TermKind.ALLIANCE,
    TermKind.VASSAL,
    TermKind.SWORN_PROMISE,
    TermKind.CONDITIONAL,
)
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
INHERITED_MEMORY_TEMPLATES = {
    PACT_SIGNED: "Your predecessor sealed a non-aggression pact with {subject} {when}.",
    TALKS_REFUSED: "Your predecessor refused {subject}'s request for a pact {when}.",
    TALKS_BROKEN_OFF: "Your predecessor broke off talks with {subject} {when}.",
}


def _mood(opinion: int) -> str:
    if opinion >= OPINION_WARM:
        return MOOD_WARM
    if opinion <= OPINION_COLD:
        return MOOD_HOSTILE
    return MOOD_GUARDED


def _when(turns_ago: int) -> str:
    if turns_ago <= 0:
        return "this turn"
    if turns_ago == 1:
        return "1 turn ago"
    return f"{turns_ago} turns ago"


def _memory_note(world: WorldState, memory: MemoryState) -> str:
    subject = world.leaders.get(memory.subject_id or "")
    is_inherited = memory.kind.startswith(INHERITED_PREFIX)
    kind = memory.kind.removeprefix(INHERITED_PREFIX)
    templates = INHERITED_MEMORY_TEMPLATES if is_inherited else MEMORY_TEMPLATES
    return templates.get(kind, kind).format(
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


def _realm_id_facts(
    world: WorldState, player_id: str, counterpart_id: str
) -> list[SituationFact]:
    if world.treaty_ruleset < 1:
        return []
    return [
        SituationFact(label="Your realm id", value=counterpart_id),
        SituationFact(label="The player's realm id", value=player_id),
        _table_regions_fact(world, player_id, counterpart_id),
    ]


def _table_regions_fact(
    world: WorldState, player_id: str, counterpart_id: str
) -> SituationFact:
    region_ids = sorted(
        region_id
        for region_id, region in world.regions.items()
        if region.owner_id in (player_id, counterpart_id)
    )
    return SituationFact(label="Regions at the table", value=", ".join(region_ids))


def _other_realms_fact(
    world: WorldState, player_id: str, counterpart_id: str
) -> SituationFact:
    others = sorted(
        faction_id
        for faction_id, faction in world.factions.items()
        if faction_id not in (player_id, counterpart_id) and not faction.is_destroyed
    )
    return SituationFact(label="Other realms", value=", ".join(others))


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
                ),
                _other_realms_fact(world, player, counterpart_faction_id),
                *_realm_id_facts(world, player, counterpart_faction_id),
            ],
        ),
        participants=[_participant(world, leader, scenario, opinion)],
        hidden_limits=HiddenLimits(
            acceptance=limits,
            grudges=build_grudges(world, scenario, leader, player),
        ),
        allowed_outcomes=[_negotiation_spec(world, scenario)],
        exchange_cap=negotiation.NEGOTIATION_EXCHANGE_CAP,
        default_outcome=TermsCardOutcome(result=TermsResult.REFUSED),
    )
    return require_valid_package(package)


def _negotiation_spec(world: WorldState, scenario: StrategyScenario) -> TermsCardSpec:
    rules = scenario.negotiation
    prices = {
        TermKind.NON_AGGRESSION: rules.pact_value_per_turn,
        TermKind.SWORN_PROMISE: UNPRICED,
    }
    kinds = _negotiation_term_kinds(rules.allowed_term_kinds)
    if world.treaty_ruleset >= 1:
        tuning = scenario.tuning.treaty
        prices[TermKind.TRADE_DEAL] = tuning.trade_value_per_turn
        prices[TermKind.MILITARY_ACCESS] = tuning.access_value_per_turn
        kinds = list(PEACETIME_CLAUSE_KINDS)
    return TermsCardSpec(
        allowed_term_kinds=kinds,
        price_by_term_kind=prices,
        max_duration_turns=rules.max_pact_turns,
    )


def _negotiation_term_kinds(configured: list[TermKind]) -> list[TermKind]:
    if TermKind.SWORN_PROMISE in configured:
        return list(configured)
    return [*configured, TermKind.SWORN_PROMISE]


def _peace_term_kinds(world: WorldState) -> list[TermKind]:
    kinds = list(PEACE_TERM_KINDS)
    if world.treaty_ruleset >= 1:
        kinds.append(TermKind.CONDITIONAL)
    return kinds


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
        hidden_limits=HiddenLimits(
            acceptance=limits,
            grudges=build_grudges(world, scenario, leader, player),
            peace_brief=build_peace_brief(
                world, scenario, player, counterpart_faction_id, war
            ),
        ),
        allowed_outcomes=[
            TermsCardSpec(
                allowed_term_kinds=_peace_term_kinds(world),
                price_by_term_kind={},
                war_score_available=side_score(war, player) if war else 0,
            )
        ],
        exchange_cap=negotiation.NEGOTIATION_EXCHANGE_CAP,
        default_outcome=TermsCardOutcome(result=TermsResult.REFUSED),
    )
    return require_valid_package(package)
