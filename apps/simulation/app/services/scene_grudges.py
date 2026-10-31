from dataclasses import dataclass

from app.engine.diplomacy.grounds import current_strength
from app.engine.succession.opinions import INHERITED_PREFIX
from app.models.api_scenes import VoicedGrudgeView
from app.models.persistence import SceneExchangeRow
from app.models.world_character import LeaderState
from app.models.world_diplomacy import GroundState
from app.models.world_state import WorldState
from strategy_contracts.diplomacy import GroundKind
from strategy_contracts.limits import MAX_GRUDGES_PER_SCENE
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.scene import Grudge, GrudgeBand, GrudgeSource, ScenePackage

BURNING_AT = 50
FIRM_AT = 20
COALITION_PREFIX = "coalition:"
COALITION_TEXT = "You are the target of a coalition they joined."
CAUSE_TEXT = {
    "declined_overture": "You turned away their offer of friendship.",
    "denounced_alliance": "You denounced your alliance with them.",
    "declined_for_other_side": "You refused their call because you backed the other side.",
    "refused_call": "You refused their call to arms.",
    "refused_demand": "You refused their demand.",
    "refused_protection": "You refused them your protection.",
}
GROUND_TEXT = {
    GroundKind.CLAIM: "They claim {region}, which you hold.",
    GroundKind.BROKEN_PROMISE: "You broke a promise to them.",
    GroundKind.INSULT: "You insulted them.",
    GroundKind.HOLY_WAR: "They hold your faith in enmity.",
    GroundKind.REFUSED_DEMAND: "You refused a demand of theirs.",
    GroundKind.INDEPENDENCE: "They have a cause for independence from you.",
}
UNKNOWN_REGION = "land"


@dataclass(frozen=True)
class _Candidate:
    magnitude: int
    text: str
    source: GrudgeSource
    is_inherited: bool
    predecessor_name: str | None


def _band(magnitude: int) -> GrudgeBand:
    if magnitude >= BURNING_AT:
        return GrudgeBand.BURNING
    if magnitude >= FIRM_AT:
        return GrudgeBand.FIRM
    return GrudgeBand.FAINT


def _cause_text(cause: str) -> str:
    if cause.startswith(COALITION_PREFIX):
        return COALITION_TEXT
    known = CAUSE_TEXT.get(cause)
    if known is not None:
        return known
    if " " in cause:
        return cause
    return cause.replace("_", " ").capitalize() + "."


def _latest_predecessor_name(
    world: WorldState, faction_id: str, own_id: str
) -> str | None:
    dead = [
        leader
        for leader in world.leaders.values()
        if leader.faction_id == faction_id
        and not leader.is_alive
        and leader.id != own_id
    ]
    return dead[-1].name if dead else None


def _opinion_candidates(
    world: WorldState, leader: LeaderState, player_leader_id: str | None
) -> list[_Candidate]:
    opinion = leader.opinions.get(player_leader_id or "")
    if opinion is None:
        return []
    predecessor = _latest_predecessor_name(world, leader.faction_id, leader.id)
    candidates = []
    for reason in opinion.reasons:
        if reason.value >= 0:
            continue
        is_inherited = reason.cause.startswith(INHERITED_PREFIX)
        cause = reason.cause.removeprefix(INHERITED_PREFIX)
        candidates.append(
            _Candidate(
                magnitude=-reason.value,
                text=_cause_text(cause),
                source=GrudgeSource.OPINION,
                is_inherited=is_inherited,
                predecessor_name=predecessor if is_inherited else None,
            )
        )
    return candidates


def _region_name(scenario: StrategyScenario, region_id: str | None) -> str:
    region = next((item for item in scenario.map.regions if item.id == region_id), None)
    return UNKNOWN_REGION if region is None else region.name


def _ground_candidate(
    world: WorldState,
    scenario: StrategyScenario,
    leader: LeaderState,
    ground: GroundState,
) -> _Candidate | None:
    strength = current_strength(ground, leader, scenario, world.clock.turn)
    if strength <= 0:
        return None
    text = GROUND_TEXT[ground.kind].format(
        region=_region_name(scenario, ground.region_id)
    )
    previous = world.leaders.get(ground.inherited_from_leader_id or "")
    return _Candidate(
        magnitude=strength,
        text=text,
        source=GrudgeSource.GROUND,
        is_inherited=previous is not None,
        predecessor_name=None if previous is None else previous.name,
    )


def _ground_candidates(
    world: WorldState,
    scenario: StrategyScenario,
    leader: LeaderState,
    player_faction_id: str,
) -> list[_Candidate]:
    held = [
        ground
        for ground in world.grounds
        if ground.holder_leader_id == leader.id
        and ground.target_faction_id == player_faction_id
    ]
    found = [_ground_candidate(world, scenario, leader, ground) for ground in held]
    return [item for item in found if item is not None]


def build_grudges(
    world: WorldState,
    scenario: StrategyScenario,
    leader: LeaderState,
    player_faction_id: str,
) -> list[Grudge]:
    """Strongest first, capped, ids fixed by sort order so the prompt prefix is stable."""
    player_leader_id = world.factions[player_faction_id].leader_id
    candidates = _opinion_candidates(world, leader, player_leader_id)
    candidates += _ground_candidates(world, scenario, leader, player_faction_id)
    ranked = sorted(
        candidates, key=lambda item: (-item.magnitude, item.source.value, item.text)
    )[:MAX_GRUDGES_PER_SCENE]
    return [
        Grudge(
            id=f"g{position}",
            text=item.text,
            source=item.source,
            band=_band(item.magnitude),
            is_inherited=item.is_inherited,
            predecessor_name=item.predecessor_name,
        )
        for position, item in enumerate(ranked, start=1)
    ]


def validated_citations(package: ScenePackage, cited_ids: list[str]) -> list[str]:
    """Only ids the package actually holds survive, once each, in the order cited."""
    known = {item.id for item in _package_grudges(package)}
    seen: list[str] = []
    for grudge_id in cited_ids:
        if grudge_id in known and grudge_id not in seen:
            seen.append(grudge_id)
    return seen


def _package_grudges(package: ScenePackage) -> list[Grudge]:
    return package.hidden_limits.grudges if package.hidden_limits else []


def voiced_grudges(
    package: ScenePackage, exchanges: list[SceneExchangeRow]
) -> list[VoicedGrudgeView]:
    voiced_ids = [gid for row in exchanges for gid in row.cited_grudge_ids]
    by_id = {item.id: item for item in _package_grudges(package)}
    ordered = dict.fromkeys(gid for gid in voiced_ids if gid in by_id)
    return [
        VoicedGrudgeView(
            text=by_id[gid].text,
            band=by_id[gid].band,
            is_inherited=by_id[gid].is_inherited,
            predecessor_name=by_id[gid].predecessor_name,
        )
        for gid in ordered
    ]
