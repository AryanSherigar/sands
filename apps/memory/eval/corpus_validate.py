"""Fixture validation: a corpus that fails here never reaches a run."""

import sys
from collections import Counter
from pathlib import Path

from app.config import get_settings
from app.services.accepted_fact_mapper import canonical_value
from app.services.fact_text import render_fact_text
from app.services.span_splitter import split_spans

from eval.baseline_text import RECENT_WINDOW_TURNS
from eval.corpus_loader import Campaign, load_campaign
from eval.corpus_models import (
    MEASURED_CLASSES,
    MIN_PROBES_PER_CLASS,
    PlantDef,
    ProbeDef,
    TurnDef,
)

FACT_LIKE_KINDS = {"fact", "relation", "supersession"}


def _duplicates(values: list[str]) -> list[str]:
    return [value for value, count in Counter(values).items() if count > 1]


def _check_fact_refs(campaign: Campaign) -> list[str]:
    entity_keys = {entity.key for entity in campaign.scenario.entities}
    references = [
        (fact.key, key)
        for fact in campaign.scenario.facts
        for key in (fact.subject_key, fact.object_key)
        if key is not None
    ]
    return [
        f"fact {fact_key} references unknown entity {key}"
        for fact_key, key in references
        if key not in entity_keys
    ]


def _check_scenario(campaign: Campaign) -> list[str]:
    scenario = campaign.scenario
    entity_keys = {entity.key for entity in scenario.entities}
    errors = [
        f"duplicate entity key {key}"
        for key in _duplicates([entity.key for entity in scenario.entities])
    ]
    errors += [
        f"duplicate fact key {key}"
        for key in _duplicates([fact.key for fact in scenario.facts])
    ]
    if scenario.player_entity_key and scenario.player_entity_key not in entity_keys:
        errors.append(f"unknown player entity {scenario.player_entity_key}")
    if not scenario.participants:
        errors.append("scenario has no participants")
    return errors + _check_fact_refs(campaign)


def _check_turn_keys(campaign: Campaign, turns: list[TurnDef], label: str) -> list[str]:
    entity_keys = {entity.key for entity in campaign.scenario.entities}
    fact_keys = {fact.key for fact in campaign.scenario.facts}
    participant_keys = {item.key for item in campaign.scenario.participants}
    errors: list[str] = []
    for turn in turns:
        if turn.participant_key not in participant_keys:
            errors.append(f"{label} turn {turn.turn_number}: unknown participant")
        used = [d.entity_key for d in turn.delta] + turn.snapshot.scene_entity_keys
        errors += [
            f"{label} turn {turn.turn_number}: unknown entity {key}"
            for key in used
            if key not in entity_keys
        ]
        snapshot_facts = (
            turn.snapshot.revealed_fact_keys
            + turn.snapshot.active_conditional_fact_keys
        )
        errors += [
            f"{label} turn {turn.turn_number}: unknown fact {key}"
            for key in snapshot_facts
            if key not in fact_keys
        ]
    return errors


def _check_turn_numbers(turns: list[TurnDef], label: str) -> list[str]:
    numbers = [turn.turn_number for turn in turns]
    if numbers != list(range(1, len(turns) + 1)):
        return [f"{label} turns are not numbered 1..{len(turns)} in order"]
    return []


def _plant_haystack(campaign: Campaign, plant: PlantDef) -> str | None:
    scenario = campaign.scenario
    if plant.source == "lore":
        return scenario.world_lore
    if plant.source == "card":
        cards = [
            card.content for card in scenario.cards if card.card_id == plant.source_ref
        ]
        return cards[0] if cards else None
    if plant.source == "authored_fact":
        return _authored_fact_text(campaign, plant)
    if plant.source == "delta":
        return _delta_fact_text(campaign, plant)
    turns = [turn for turn in campaign.turns if turn.turn_number == plant.turn]
    return f"{turns[0].action_text}\n{turns[0].narration_text}" if turns else None


def _delta_fact_text(campaign: Campaign, plant: PlantDef) -> str | None:
    names = {entity.key: entity.canonical_name for entity in campaign.scenario.entities}
    turns = [turn for turn in campaign.turns if turn.turn_number == plant.turn]
    for delta in turns[0].delta if turns else []:
        if f"{delta.entity_key}.{delta.attribute}" == plant.source_ref:
            return render_fact_text(
                names.get(delta.entity_key, ""),
                delta.attribute,
                canonical_value(delta.after),
            )
    return None


def _authored_fact_text(campaign: Campaign, plant: PlantDef) -> str | None:
    scenario = campaign.scenario
    names = {entity.key: entity.canonical_name for entity in scenario.entities}
    facts = [fact for fact in scenario.facts if fact.key == plant.fact_key]
    if not facts:
        return None
    fact = facts[0]
    object_text = fact.object_literal or names.get(fact.object_key or "", "")
    return render_fact_text(
        names.get(fact.subject_key, ""), fact.predicate, object_text
    )


def _check_plant_anchor(campaign: Campaign, plant: PlantDef) -> list[str]:
    haystack = _plant_haystack(campaign, plant)
    if haystack is None:
        return [f"plant {plant.plant_id}: source {plant.source} not found"]
    count = haystack.count(plant.anchor_text)
    if count == 0 or (count > 1 and plant.kind != "entity_link"):
        return [
            f"plant {plant.plant_id}: anchor found {count} times, expected exactly once"
        ]
    return []


def _plant_sources(campaign: Campaign, plant: PlantDef) -> list[str]:
    if plant.source == "turn":
        turns = [t for t in campaign.turns if t.turn_number == plant.turn]
        return [turns[0].action_text, turns[0].narration_text] if turns else []
    haystack = _plant_haystack(campaign, plant)
    return [haystack] if haystack else []


def _check_anchor_in_one_span(campaign: Campaign, plant: PlantDef) -> list[str]:
    if plant.kind == "entity_link" or plant.source == "delta":
        return []
    settings = get_settings()
    spans = [
        span.text
        for text in _plant_sources(campaign, plant)
        for span in split_spans(
            text, "V", settings.span_max_tokens, settings.span_chars_per_token
        )
    ]
    if any(plant.anchor_text in text for text in spans):
        return []
    return [f"plant {plant.plant_id}: anchor does not fall inside a single span"]


def _check_supersedes_target(plant: PlantDef, plant_ids: set[str]) -> list[str]:
    if plant.supersedes_plant_id and plant.supersedes_plant_id not in plant_ids:
        return [f"plant {plant.plant_id}: supersedes unknown plant"]
    return []


def _check_plant_shape(plant: PlantDef, plant_ids: set[str]) -> list[str]:
    errors: list[str] = []
    if plant.kind == "negated" and not (plant.subject_key and plant.predicate):
        errors.append(f"plant {plant.plant_id}: negated plant needs the denied claim")
    if plant.kind in FACT_LIKE_KINDS and not (plant.subject_key and plant.predicate):
        errors.append(
            f"plant {plant.plant_id}: fact-like plant needs subject and predicate"
        )
    if plant.kind == "commitment" and not (plant.commitment_kind and plant.status):
        errors.append(f"plant {plant.plant_id}: commitment needs kind and status")
    if plant.kind == "supersession" and plant.supersedes_plant_id not in plant_ids:
        errors.append(f"plant {plant.plant_id}: supersession target unknown")
    if plant.source == "authored_fact" and plant.turn != 0:
        errors.append(f"plant {plant.plant_id}: authored plant must be turn 0")
    if plant.source in {"turn", "delta"} and plant.turn < 1:
        errors.append(f"plant {plant.plant_id}: turn plant needs turn >= 1")
    return errors


def _check_rejected_plant(campaign: Campaign, plant: PlantDef) -> list[str]:
    if plant.kind != "rejected":
        return []
    turns = [turn for turn in campaign.turns if turn.turn_number == plant.turn]
    if not turns or not turns[0].rejected_calls:
        return [
            f"plant {plant.plant_id}: rejected plant needs a turn with rejected calls"
        ]
    return []


def _check_plants(campaign: Campaign) -> list[str]:
    plant_ids = {plant.plant_id for plant in campaign.plants}
    errors = [
        f"duplicate plant id {key}"
        for key in _duplicates([plant.plant_id for plant in campaign.plants])
    ]
    for plant in campaign.plants:
        errors += _check_plant_anchor(campaign, plant)
        errors += _check_anchor_in_one_span(campaign, plant)
        errors += _check_supersedes_target(plant, plant_ids)
        errors += _check_plant_shape(plant, plant_ids)
        errors += _check_rejected_plant(campaign, plant)
    return errors


def _is_inside_window(plant: PlantDef, probe: ProbeDef, is_required: bool) -> bool:
    is_turn_text = plant.source == "turn"
    return (
        is_required
        and is_turn_text
        and probe.at_turn - plant.turn < RECENT_WINDOW_TURNS
    )


def _check_plant_timing(
    probe: ProbeDef, plants: dict[str, PlantDef], plant_id: str
) -> list[str]:
    plant = plants.get(plant_id)
    if plant is None:
        return [f"probe {probe.probe_id}: unknown plant {plant_id}"]
    if plant.turn > probe.at_turn:
        return [f"probe {probe.probe_id}: plant {plant_id} is after the probe"]
    if _is_inside_window(plant, probe, plant_id in probe.required):
        return [f"probe {probe.probe_id}: plant {plant_id} is inside the recent window"]
    return []


def _both_required_and_forbidden(
    probe: ProbeDef, plants: dict[str, PlantDef]
) -> set[str]:
    return {
        plant_id
        for plant_id in set(probe.required) & set(probe.forbidden)
        if plant_id not in plants or plants[plant_id].kind != "negated"
    }


def _check_probe_refs(
    probe: ProbeDef,
    plants: dict[str, PlantDef],
    participant_keys: set[str],
    turn_count: int,
) -> list[str]:
    errors: list[str] = []
    if probe.at_turn > turn_count:
        errors.append(f"probe {probe.probe_id}: at_turn beyond the campaign")
    if probe.actor_key not in participant_keys:
        errors.append(f"probe {probe.probe_id}: unknown actor")
    for plant_id in probe.required + probe.forbidden + probe.distractors:
        errors += _check_plant_timing(probe, plants, plant_id)
    if set(probe.distractors) & set(probe.required + probe.forbidden):
        errors.append(
            f"probe {probe.probe_id}: a distractor is also required or forbidden"
        )
    if _both_required_and_forbidden(probe, plants):
        errors.append(f"probe {probe.probe_id}: a plant is both required and forbidden")
    if not probe.required and not probe.forbidden and not probe.forbidden_anchors:
        errors.append(f"probe {probe.probe_id}: asserts nothing")
    return errors


def _check_class_rules(
    campaign: Campaign, probe: ProbeDef, plants: dict[str, PlantDef]
) -> list[str]:
    superseded = {
        p.supersedes_plant_id for p in campaign.plants if p.supersedes_plant_id
    }
    errors: list[str] = []
    if probe.failure_class == "knowledge_update":
        errors += [
            f"probe {probe.probe_id}: required plant {pid} is not a supersession"
            for pid in probe.required
            if pid in plants and plants[pid].kind != "supersession"
        ]
        errors += [
            f"probe {probe.probe_id}: forbidden plant {pid} was never superseded"
            for pid in probe.forbidden
            if pid not in superseded
        ]
    if probe.failure_class == "rejected_mutation":
        errors += [
            f"probe {probe.probe_id}: forbidden plant {pid} is not a rejected plant"
            for pid in probe.forbidden
            if pid in plants and plants[pid].kind != "rejected"
        ]
    if probe.failure_class == "isolation":
        errors += _check_isolation(campaign, probe)
    return errors


def _check_isolation(campaign: Campaign, probe: ProbeDef) -> list[str]:
    if not probe.forbidden_anchors:
        return [f"probe {probe.probe_id}: isolation probe needs forbidden_anchors"]
    main_text = "\n".join(
        f"{t.action_text}\n{t.narration_text}" for t in campaign.turns
    )
    decoy_text = "\n".join(
        f"{t.action_text}\n{t.narration_text}" for t in campaign.decoy_turns
    )
    errors: list[str] = []
    for anchor in probe.forbidden_anchors:
        if anchor not in decoy_text:
            errors.append(f"probe {probe.probe_id}: anchor {anchor!r} not in the decoy")
        if anchor in main_text:
            errors.append(
                f"probe {probe.probe_id}: anchor {anchor!r} appears in the main campaign"
            )
    return errors


def _check_probes(campaign: Campaign) -> list[str]:
    plants = {plant.plant_id: plant for plant in campaign.plants}
    participant_keys = {item.key for item in campaign.scenario.participants}
    errors = [
        f"duplicate probe id {key}"
        for key in _duplicates([probe.probe_id for probe in campaign.probes])
    ]
    for probe in campaign.probes:
        errors += _check_probe_refs(
            probe, plants, participant_keys, len(campaign.turns)
        )
        errors += _check_class_rules(campaign, probe, plants)
    return errors


def validate_campaign(campaign: Campaign) -> list[str]:
    errors = _check_scenario(campaign)
    errors += _check_turn_numbers(campaign.turns, "main")
    errors += _check_turn_numbers(campaign.decoy_turns, "decoy")
    errors += _check_turn_keys(campaign, campaign.turns, "main")
    errors += _check_turn_keys(campaign, campaign.decoy_turns, "decoy")
    errors += _check_plants(campaign)
    errors += _check_probes(campaign)
    return errors


def validate_class_minimums(campaigns: list[Campaign]) -> list[str]:
    counts = Counter(
        probe.failure_class for campaign in campaigns for probe in campaign.probes
    )
    return [
        f"class {name} has {counts[name]} probes, needs {MIN_PROBES_PER_CLASS}"
        for name in MEASURED_CLASSES
        if counts[name] < MIN_PROBES_PER_CLASS
    ]


def main(corpus_root: Path) -> int:
    campaigns = [
        load_campaign(path) for path in sorted(corpus_root.iterdir()) if path.is_dir()
    ]
    errors = [e for campaign in campaigns for e in validate_campaign(campaign)]
    errors += validate_class_minimums(campaigns)
    for error in errors:
        print(error)
    return 1 if errors else 0


if __name__ == "__main__":
    root = (
        Path(sys.argv[sys.argv.index("--corpus") + 1])
        if "--corpus" in sys.argv
        else Path("eval/corpus")
    )
    raise SystemExit(main(root))
