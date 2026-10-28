from collections import Counter
from collections.abc import Callable, Iterable, Iterator
from enum import Enum

from strategy_contracts.base import StrictModel
from strategy_contracts.conditions import SUBJECT_PLACEHOLDER, condition_depth
from strategy_contracts.event_catalog import BUILTIN_EVENT_IDS
from strategy_contracts.events import EffectSpec, EventDefinition
from strategy_contracts.limits import MAX_CONDITION_DEPTH
from strategy_contracts.map_graph import (
    find_disconnected_groups,
    find_duplicate_region_ids,
    find_one_way_links,
)
from strategy_contracts.scenario import EndingKind, StrategyScenario
from strategy_contracts.stances import BUILTIN_STANCES
from strategy_contracts.traits import BUILTIN_TRAITS

MIN_FACTIONS_FOR_LONG_PLAY = 4
MIN_REGIONS_FOR_LONG_PLAY = 20
MAJORITY_NUMERATOR = 2
LOPSIDED_TROOP_RATIO = 4


class IssueCode(str, Enum):
    DUPLICATE_ID = "duplicate_id"
    MAP_DISCONNECTED = "map_disconnected"
    MAP_ONE_WAY_LINK = "map_one_way_link"
    DANGLING_REFERENCE = "dangling_reference"
    FACTION_HAS_NO_REGION = "faction_has_no_region"
    FACTION_HAS_NO_CAPITAL = "faction_has_no_capital"
    FACTION_HAS_NO_LEADER = "faction_has_no_leader"
    LEADER_HAS_NO_TRAIT = "leader_has_no_trait"
    LEADER_HAS_NO_AMBITION = "leader_has_no_ambition"
    NO_PLAYABLE_FACTION = "no_playable_faction"
    NO_VICTORY_ENDING = "no_victory_ending"
    NO_DEFEAT_ENDING = "no_defeat_ending"
    CONDITION_TOO_DEEP = "condition_too_deep"
    FEW_FACTIONS = "few_factions"
    FEW_REGIONS = "few_regions"
    LEADER_HAS_NO_HISTORY = "leader_has_no_history"
    LOPSIDED_START = "lopsided_start"
    STANCE_ID_COLLISION = "stance_id_collision"
    UNKNOWN_STANCE_REFERENCE = "unknown_stance_reference"
    EMPTY_STANCE_MENU = "empty_stance_menu"
    INVALID_VASSALAGE = "invalid_vassalage"


class Issue(StrictModel):
    code: IssueCode
    path: str
    message: str


class PublishReport(StrictModel):
    blocking: list[Issue]
    warnings: list[Issue]

    @property
    def is_publishable(self) -> bool:
        return not self.blocking


Check = Callable[[StrategyScenario], list[Issue]]


def _issue(code: IssueCode, path: str, message: str) -> Issue:
    return Issue(code=code, path=path, message=message)


def _check_duplicate_ids(scenario: StrategyScenario) -> list[Issue]:
    groups = {
        "region": find_duplicate_region_ids(scenario.map),
        "faction": _duplicates(faction.id for faction in scenario.factions),
        "leader": _duplicates(leader.id for leader in scenario.leaders),
        "event": _duplicates(event.id for event in scenario.events),
    }
    return [
        _issue(IssueCode.DUPLICATE_ID, kind, f"duplicate {kind} id '{value}'")
        for kind, values in groups.items()
        for value in values
    ]


def _duplicates(values: Iterable[str]) -> list[str]:
    counts = Counter(values)
    return sorted(value for value, count in counts.items() if count > 1)


def _check_map_graph(scenario: StrategyScenario) -> list[Issue]:
    issues = [
        _issue(
            IssueCode.MAP_ONE_WAY_LINK,
            f"map.regions[{region_id}].neighbor_ids",
            f"'{region_id}' lists '{neighbor_id}' but not the reverse",
        )
        for region_id, neighbor_id in find_one_way_links(scenario.map)
    ]
    if find_disconnected_groups(scenario.map):
        issues.append(
            _issue(IssueCode.MAP_DISCONNECTED, "map.regions", "map is not connected")
        )
    return issues


def _scenario_id_sets(scenario: StrategyScenario) -> dict[str, set[str]]:
    trait_ids = {trait.id for trait in BUILTIN_TRAITS}
    trait_ids |= {trait.id for trait in scenario.custom_traits}
    return {
        "region": {region.id for region in scenario.map.regions},
        "faction": {faction.id for faction in scenario.factions},
        "leader": {leader.id for leader in scenario.leaders},
        "governor": {governor.id for governor in scenario.governors},
        "commander": {commander.id for commander in scenario.commanders},
        "faith": {faith.id for faith in scenario.faiths},
        "ambition": {ambition.id for ambition in scenario.ambitions},
        "trait": trait_ids,
    }


Reference = tuple[str, str | None, str]


def _map_references(scenario: StrategyScenario) -> Iterator[Reference]:
    for index, region in enumerate(scenario.map.regions):
        for position, neighbor_id in enumerate(region.neighbor_ids):
            yield (
                f"map.regions[{index}].neighbor_ids[{position}]",
                neighbor_id,
                "region",
            )
    for index, road in enumerate(scenario.map.roads):
        yield f"map.roads[{index}].region_a", road.region_a, "region"
        yield f"map.roads[{index}].region_b", road.region_b, "region"


def _faction_references(scenario: StrategyScenario) -> Iterator[Reference]:
    for index, faction in enumerate(scenario.factions):
        yield (
            f"factions[{index}].capital_region_id",
            faction.capital_region_id,
            "region",
        )
        yield f"factions[{index}].leader_id", faction.leader_id, "leader"


def _trait_references(base: str, trait_ids: list[str]) -> Iterator[Reference]:
    for position, trait_id in enumerate(trait_ids):
        yield f"{base}.trait_ids[{position}]", trait_id, "trait"


def _leader_references(scenario: StrategyScenario) -> Iterator[Reference]:
    for index, leader in enumerate(scenario.leaders):
        base = f"leaders[{index}]"
        yield f"{base}.faction_id", leader.faction_id, "faction"
        yield from _trait_references(base, leader.trait_ids)
        for position, ambition_id in enumerate(leader.ambition_ids):
            yield f"{base}.ambition_ids[{position}]", ambition_id, "ambition"


def _governor_and_commander_references(
    scenario: StrategyScenario,
) -> Iterator[Reference]:
    for index, governor in enumerate(scenario.governors):
        base = f"governors[{index}]"
        yield f"{base}.region_id", governor.region_id, "region"
        yield from _trait_references(base, governor.trait_ids)
    for index, commander in enumerate(scenario.commanders):
        base = f"commanders[{index}]"
        yield f"{base}.faction_id", commander.faction_id, "faction"
        yield from _trait_references(base, commander.trait_ids)


def _starting_region_references(scenario: StrategyScenario) -> Iterator[Reference]:
    for index, setup in enumerate(scenario.starting.regions):
        base = f"starting.regions[{index}]"
        yield f"{base}.region_id", setup.region_id, "region"
        yield f"{base}.owner_id", setup.owner_id, "faction"
        yield f"{base}.faith_id", setup.faith_id, "faith"
        yield f"{base}.governor_id", setup.governor_id, "governor"


def _starting_army_references(scenario: StrategyScenario) -> Iterator[Reference]:
    for index, army in enumerate(scenario.starting.armies):
        base = f"starting.armies[{index}]"
        yield f"{base}.owner_id", army.owner_id, "faction"
        yield f"{base}.location_id", army.location_id, "region"
        yield f"{base}.commander_id", army.commander_id, "commander"


def _starting_diplomacy_references(scenario: StrategyScenario) -> Iterator[Reference]:
    for index, relation in enumerate(scenario.starting.relations):
        yield f"starting.relations[{index}].faction_a", relation.faction_a, "faction"
        yield f"starting.relations[{index}].faction_b", relation.faction_b, "faction"
    for index, claim in enumerate(scenario.starting.claims):
        yield f"starting.claims[{index}].faction_id", claim.faction_id, "faction"
        yield f"starting.claims[{index}].region_id", claim.region_id, "region"
    for index, grudge in enumerate(scenario.starting.grudges):
        yield f"starting.grudges[{index}].holder_id", grudge.holder_id, "leader"
        yield f"starting.grudges[{index}].target_id", grudge.target_id, "leader"


def _negotiation_references(scenario: StrategyScenario) -> Iterator[Reference]:
    for index, trigger in enumerate(scenario.negotiation.triggers):
        yield (
            f"negotiation.triggers[{index}].initiator_faction_id",
            trigger.initiator_faction_id,
            "faction",
        )


REFERENCE_SOURCES: tuple[Callable[[StrategyScenario], Iterator[Reference]], ...] = (
    _map_references,
    _faction_references,
    _leader_references,
    _governor_and_commander_references,
    _starting_region_references,
    _starting_army_references,
    _starting_diplomacy_references,
    _negotiation_references,
)


def _check_references(scenario: StrategyScenario) -> list[Issue]:
    ids = _scenario_id_sets(scenario)
    return [
        _issue(IssueCode.DANGLING_REFERENCE, path, f"unknown {kind} '{value}'")
        for source in REFERENCE_SOURCES
        for path, value, kind in source(scenario)
        if value is not None and value not in ids[kind]
    ]


def _owned_region_counts(scenario: StrategyScenario) -> Counter[str]:
    return Counter(
        setup.owner_id
        for setup in scenario.starting.regions
        if setup.owner_id is not None
    )


def _check_faction_completeness(scenario: StrategyScenario) -> list[Issue]:
    owned = _owned_region_counts(scenario)
    issues: list[Issue] = []
    for index, faction in enumerate(scenario.factions):
        path = f"factions[{index}]"
        if owned[faction.id] == 0:
            issues.append(
                _issue(
                    IssueCode.FACTION_HAS_NO_REGION,
                    path,
                    f"'{faction.id}' owns no region",
                )
            )
        if faction.capital_region_id is None:
            issues.append(
                _issue(
                    IssueCode.FACTION_HAS_NO_CAPITAL,
                    path,
                    f"'{faction.id}' has no capital",
                )
            )
        if faction.leader_id is None:
            issues.append(
                _issue(
                    IssueCode.FACTION_HAS_NO_LEADER,
                    path,
                    f"'{faction.id}' has no leader",
                )
            )
    return issues


def _check_leaders(scenario: StrategyScenario) -> list[Issue]:
    issues: list[Issue] = []
    for index, leader in enumerate(scenario.leaders):
        path = f"leaders[{index}]"
        if not leader.trait_ids:
            issues.append(
                _issue(
                    IssueCode.LEADER_HAS_NO_TRAIT, path, f"'{leader.id}' has no trait"
                )
            )
        if not leader.ambition_ids:
            issues.append(
                _issue(
                    IssueCode.LEADER_HAS_NO_AMBITION,
                    path,
                    f"'{leader.id}' has no ambition",
                )
            )
    return issues


def _check_playable(scenario: StrategyScenario) -> list[Issue]:
    if any(faction.is_playable for faction in scenario.factions):
        return []
    return [_issue(IssueCode.NO_PLAYABLE_FACTION, "factions", "no playable faction")]


def _check_endings(scenario: StrategyScenario) -> list[Issue]:
    if scenario.is_using_default_endings:
        return []
    kinds = {ending.kind for ending in scenario.endings}
    issues: list[Issue] = []
    if EndingKind.VICTORY not in kinds:
        issues.append(
            _issue(IssueCode.NO_VICTORY_ENDING, "endings", "no victory ending")
        )
    if EndingKind.DEFEAT not in kinds:
        issues.append(_issue(IssueCode.NO_DEFEAT_ENDING, "endings", "no defeat ending"))
    return issues


def _conditions_with_paths(scenario: StrategyScenario) -> list[tuple[str, object]]:
    pairs: list[tuple[str, object]] = []
    pairs += [
        (f"ambitions[{i}].condition", a.condition)
        for i, a in enumerate(scenario.ambitions)
    ]
    pairs += [
        (f"endings[{i}].condition", e.condition) for i, e in enumerate(scenario.endings)
    ]
    pairs += [
        (f"events[{i}].tiers[{j}].trigger", tier.trigger)
        for i, event in enumerate(scenario.events)
        for j, tier in enumerate(event.tiers)
    ]
    return pairs


def _check_condition_depth(scenario: StrategyScenario) -> list[Issue]:
    return [
        _issue(IssueCode.CONDITION_TOO_DEEP, path, "condition nests too deeply")
        for path, condition in _conditions_with_paths(scenario)
        if condition_depth(condition) > MAX_CONDITION_DEPTH
    ]


def _check_event_references(scenario: StrategyScenario) -> list[Issue]:
    known = (
        {region.id for region in scenario.map.regions}
        | {faction.id for faction in scenario.factions}
        | {leader.id for leader in scenario.leaders}
    )
    issues = [
        _issue(
            IssueCode.DANGLING_REFERENCE,
            f"events[{i}].neglect_effects",
            f"effect targets unknown entity '{effect.target_id}'",
        )
        for i, event in enumerate(scenario.events)
        for effect in _all_effects(event)
        if effect.target_id not in (None, SUBJECT_PLACEHOLDER, *known)
    ]
    issues += [
        _issue(
            IssueCode.DANGLING_REFERENCE,
            "disabled_builtin_event_ids",
            f"'{event_id}' is not a built-in event",
        )
        for event_id in scenario.disabled_builtin_event_ids
        if event_id not in BUILTIN_EVENT_IDS
    ]
    return issues


def _all_effects(event: EventDefinition) -> list[EffectSpec]:
    return event.neglect_effects + [
        effect for choice in event.choices for effect in choice.effects
    ]


def _check_stance_ids(scenario: StrategyScenario) -> list[Issue]:
    builtin_ids = {stance.id for stance in BUILTIN_STANCES}
    custom_ids = [stance.id for stance in scenario.custom_stances]
    clashing = sorted(builtin_ids & set(custom_ids))
    return [
        _issue(
            IssueCode.STANCE_ID_COLLISION,
            "custom_stances",
            f"stance id '{value}' is already taken",
        )
        for value in sorted({*clashing, *_duplicates(custom_ids)})
    ]


def _check_faction_stance_menus(scenario: StrategyScenario) -> list[Issue]:
    known_ids = {stance.id for stance in BUILTIN_STANCES}
    known_ids |= {stance.id for stance in scenario.custom_stances}
    issues: list[Issue] = []
    for index, faction in enumerate(scenario.factions):
        if faction.stance_ids is None:
            continue
        base = f"factions[{index}].stance_ids"
        if not faction.stance_ids:
            issues.append(
                _issue(IssueCode.EMPTY_STANCE_MENU, base, "faction has no stances")
            )
        issues.extend(
            _issue(
                IssueCode.UNKNOWN_STANCE_REFERENCE,
                f"{base}[{position}]",
                f"unknown stance '{stance_id}'",
            )
            for position, stance_id in enumerate(faction.stance_ids)
            if stance_id not in known_ids
        )
    return issues


def _check_stances(scenario: StrategyScenario) -> list[Issue]:
    return _check_stance_ids(scenario) + _check_faction_stance_menus(scenario)


def _vassal_overlords(scenario: StrategyScenario) -> list[tuple[int, str, str]]:
    return [
        (
            index,
            relation.vassalage.overlord_id,
            relation.faction_b
            if relation.vassalage.overlord_id == relation.faction_a
            else relation.faction_a,
        )
        for index, relation in enumerate(scenario.starting.relations)
        if relation.vassalage is not None
    ]


def _has_overlord_cycle(overlord_of: dict[str, str], start: str) -> bool:
    seen = {start}
    current = overlord_of.get(start)
    while current is not None:
        if current in seen:
            return True
        seen.add(current)
        current = overlord_of.get(current)
    return False


def _check_vassalages(scenario: StrategyScenario) -> list[Issue]:
    issues: list[Issue] = []
    overlord_of: dict[str, str] = {}
    for index, overlord_id, vassal_id in _vassal_overlords(scenario):
        path = f"starting.relations[{index}].vassalage"
        if vassal_id in overlord_of:
            issues.append(
                _issue(IssueCode.INVALID_VASSALAGE, path, "vassal has two overlords")
            )
        overlord_of[vassal_id] = overlord_id
    for vassal_id in sorted(overlord_of):
        if _has_overlord_cycle(overlord_of, vassal_id):
            issues.append(
                _issue(
                    IssueCode.INVALID_VASSALAGE,
                    "starting.relations",
                    "vassalages form a cycle",
                )
            )
            break
    return issues


BLOCKING_CHECKS: tuple[Check, ...] = (
    _check_duplicate_ids,
    _check_stances,
    _check_map_graph,
    _check_references,
    _check_faction_completeness,
    _check_leaders,
    _check_playable,
    _check_endings,
    _check_condition_depth,
    _check_event_references,
    _check_vassalages,
)


def _warn_size(scenario: StrategyScenario) -> list[Issue]:
    issues: list[Issue] = []
    if len(scenario.factions) < MIN_FACTIONS_FOR_LONG_PLAY:
        issues.append(
            _issue(IssueCode.FEW_FACTIONS, "factions", "may feel small for long play")
        )
    if len(scenario.map.regions) < MIN_REGIONS_FOR_LONG_PLAY:
        issues.append(
            _issue(IssueCode.FEW_REGIONS, "map.regions", "may feel small for long play")
        )
    return issues


def _warn_history(scenario: StrategyScenario) -> list[Issue]:
    return [
        _issue(
            IssueCode.LEADER_HAS_NO_HISTORY,
            f"leaders[{index}]",
            "history will be generated at playthrough start",
        )
        for index, leader in enumerate(scenario.leaders)
        if not leader.history.strip()
    ]


def _troop_totals(scenario: StrategyScenario) -> dict[str, int]:
    totals = {faction.id: 0 for faction in scenario.factions}
    for army in scenario.starting.armies:
        if army.owner_id in totals:
            totals[army.owner_id] += sum(army.troops.values())
    return totals


def _is_lopsided(scenario: StrategyScenario) -> bool:
    owned = _owned_region_counts(scenario)
    total_regions = sum(owned.values())
    if total_regions and max(owned.values()) * MAJORITY_NUMERATOR > total_regions:
        return True
    totals = list(_troop_totals(scenario).values())
    return (
        bool(totals)
        and min(totals) > 0
        and max(totals) >= LOPSIDED_TROOP_RATIO * min(totals)
    )


def _warn_lopsided(scenario: StrategyScenario) -> list[Issue]:
    if not _is_lopsided(scenario):
        return []
    return [
        _issue(
            IssueCode.LOPSIDED_START,
            "starting",
            "one faction starts far ahead of the others",
        )
    ]


WARNING_CHECKS: tuple[Check, ...] = (_warn_size, _warn_history, _warn_lopsided)


def check_publishable(scenario: StrategyScenario) -> PublishReport:
    blocking = [issue for check in BLOCKING_CHECKS for issue in check(scenario)]
    warnings = [issue for check in WARNING_CHECKS for issue in check(scenario)]
    return PublishReport(blocking=blocking, warnings=warnings)
