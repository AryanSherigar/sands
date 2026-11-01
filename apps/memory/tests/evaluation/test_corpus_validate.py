import json
from dataclasses import replace
from pathlib import Path

import pytest
from eval.corpus_loader import CorpusLoadError, load_campaign
from eval.corpus_models import MEASURED_CLASSES, DeltaDef, PlantDef, ProbeDef
from eval.corpus_validate import validate_campaign, validate_class_minimums
from eval.keys import key_uuid, turn_uuid
from eval.labels import generate_labels, write_labels
from tests.evaluation.campaign_helpers import (
    ANCHOR_DECOY,
    make_campaign,
    make_turn,
    with_probe,
)


def _probe(**overrides: object) -> ProbeDef:
    values: dict[str, object] = {
        "probe_id": "px",
        "failure_class": "long_range",
        "at_turn": 8,
        "action_text": "I ask.",
        "action_mode": "say",
        "actor_key": "p1",
        "required": ["pl_oath"],
        "expected_truth": "open",
    }
    values.update(overrides)
    return ProbeDef.model_validate(values)


def test_valid_campaign_has_no_errors() -> None:
    assert validate_campaign(make_campaign()) == []


def test_anchor_missing_from_its_turn_is_reported() -> None:
    campaign = make_campaign()
    bad = campaign.plants[0].model_copy(update={"anchor_text": "never written"})
    errors = validate_campaign(replace(campaign, plants=[bad, *campaign.plants[1:]]))
    assert any("anchor found 0 times" in error for error in errors)


def test_anchor_appearing_twice_is_reported() -> None:
    campaign = make_campaign()
    turns = [
        make_turn(1, "Mira swears to guard the ferry. Mira swears to guard the ferry."),
        *campaign.turns[1:],
    ]
    errors = validate_campaign(replace(campaign, turns=turns))
    assert any("found 2 times" in error for error in errors)


def test_probe_referencing_unknown_plant_is_reported() -> None:
    errors = validate_campaign(with_probe(make_campaign(), _probe(required=["nope"])))
    assert any("unknown plant nope" in error for error in errors)


def test_probe_before_its_plant_is_reported() -> None:
    errors = validate_campaign(
        with_probe(make_campaign(), _probe(at_turn=1, required=["pl_rej"]))
    )
    assert any("is after the probe" in error for error in errors)


def test_plant_required_and_forbidden_is_reported() -> None:
    errors = validate_campaign(
        with_probe(make_campaign(), _probe(forbidden=["pl_oath"]))
    )
    assert any("both required and forbidden" in error for error in errors)


def test_probe_beyond_campaign_is_reported() -> None:
    errors = validate_campaign(with_probe(make_campaign(), _probe(at_turn=99)))
    assert any("beyond the campaign" in error for error in errors)


def test_knowledge_update_requires_a_supersession() -> None:
    probe = _probe(
        failure_class="knowledge_update", required=["pl_oath"], forbidden=["pl_rej"]
    )
    errors = validate_campaign(with_probe(make_campaign(), probe))
    assert any("is not a supersession" in error for error in errors)
    assert any("never superseded" in error for error in errors)


def test_rejected_mutation_forbids_only_rejected_plants() -> None:
    probe = _probe(
        failure_class="rejected_mutation", required=[], forbidden=["pl_oath"]
    )
    errors = validate_campaign(with_probe(make_campaign(), probe))
    assert any("not a rejected plant" in error for error in errors)


def test_isolation_anchor_must_be_in_decoy_only() -> None:
    good = _probe(
        failure_class="isolation", required=[], forbidden_anchors=[ANCHOR_DECOY]
    )
    assert validate_campaign(with_probe(make_campaign(), good)) == []
    bad = _probe(
        probe_id="py",
        failure_class="isolation",
        required=[],
        forbidden_anchors=["Mira"],
    )
    errors = validate_campaign(with_probe(make_campaign(), bad))
    assert any("not in the decoy" in error for error in errors)


def test_turn_numbers_must_be_contiguous() -> None:
    campaign = make_campaign()
    gap = [campaign.turns[0], campaign.turns[2]]
    errors = validate_campaign(replace(campaign, turns=gap))
    assert any("not numbered" in error for error in errors)


def test_rejected_plant_needs_rejected_calls() -> None:
    campaign = make_campaign()
    turns = [
        campaign.turns[0],
        make_turn(2, "The warden's arm grows a second head."),
        campaign.turns[2],
    ]
    errors = validate_campaign(replace(campaign, turns=turns))
    assert any("needs a turn with rejected calls" in error for error in errors)


def test_class_minimums_list_every_short_class() -> None:
    errors = validate_class_minimums([make_campaign()])
    assert len(errors) == len(MEASURED_CLASSES)


def test_key_uuid_is_stable_and_scoped() -> None:
    assert key_uuid("C1", "mira") == key_uuid("C1", "mira")
    assert key_uuid("C1", "mira") != key_uuid("C2", "mira")
    assert turn_uuid("C1", "playthrough", 1) != turn_uuid("C1", "decoy_playthrough", 1)


def test_labels_skip_authored_plants_and_keep_rejected_as_forbidden() -> None:
    labels = {label.label_id: label for label in generate_labels(make_campaign())}
    assert set(labels) == {"pl_oath", "pl_rej"}
    assert labels["pl_rej"].label_type == "forbidden_fact"
    assert labels["pl_oath"].status == "open"


def test_load_campaign_without_files_raises(tmp_path: Path) -> None:
    with pytest.raises(CorpusLoadError):
        load_campaign(tmp_path)


def test_campaign_round_trips_through_files(tmp_path: Path) -> None:
    campaign = make_campaign()
    (tmp_path / "scenario.json").write_text(
        campaign.scenario.model_dump_json(), encoding="utf-8"
    )
    for name, items in (
        ("turns.jsonl", campaign.turns),
        ("decoy.jsonl", campaign.decoy_turns),
        ("plants.jsonl", campaign.plants),
        ("probes.jsonl", campaign.probes),
    ):
        (tmp_path / name).write_text(
            "\n".join(i.model_dump_json() for i in items) + "\n", encoding="utf-8"
        )
    loaded = load_campaign(tmp_path)
    assert validate_campaign(loaded) == []
    assert write_labels(tmp_path) == 2
    assert load_campaign(tmp_path).content_hash == loaded.content_hash


def test_plant_text_below_minimum_length_is_rejected() -> None:
    with pytest.raises(ValueError):
        PlantDef(plant_id="p", source="turn", turn=1, kind="fact", anchor_text="ab")


def test_anchor_split_across_spans_is_reported() -> None:
    campaign = make_campaign()
    long_sentence = "word " * 400
    anchor = f"{long_sentence}end"
    turns = [make_turn(1, anchor), *campaign.turns[1:]]
    plants = [
        campaign.plants[0].model_copy(update={"anchor_text": anchor}),
        *campaign.plants[1:],
    ]
    errors = validate_campaign(replace(campaign, turns=turns, plants=plants))
    assert any("single span" in error for error in errors)


def test_commitment_update_must_point_at_an_existing_plant() -> None:
    campaign = make_campaign()
    update = campaign.plants[0].model_copy(
        update={
            "plant_id": "pl_update",
            "supersedes_plant_id": "ghost",
            "anchor_text": "crosses the river",
        }
    )
    turns_with_anchor = campaign.turns
    errors = validate_campaign(
        replace(
            campaign,
            turns=turns_with_anchor,
            plants=[*campaign.plants, update.model_copy(update={"turn": 3})],
        )
    )
    assert any("supersedes unknown plant" in error for error in errors)


def test_delta_plant_anchor_is_the_rendered_accepted_fact() -> None:
    campaign = make_campaign()
    delta = DeltaDef(
        kind="state_mutation", entity_key="vale", attribute="hp", before=9, after=7
    )
    turns = [
        campaign.turns[0],
        campaign.turns[1].model_copy(update={"delta": [delta]}),
        *campaign.turns[2:],
    ]
    good = PlantDef(
        plant_id="pl_hp",
        source="delta",
        source_ref="vale.hp",
        turn=2,
        kind="fact",
        anchor_text="Captain Vale hp 7",
        subject_key="vale",
        predicate="hp",
        object_literal="7",
    )
    bad = good.model_copy(
        update={"plant_id": "pl_bad", "anchor_text": "Captain Vale hp 8"}
    )
    assert (
        validate_campaign(
            replace(campaign, turns=turns, plants=[*campaign.plants, good])
        )
        == []
    )
    errors = validate_campaign(
        replace(campaign, turns=turns, plants=[*campaign.plants, bad])
    )
    assert any("anchor found 0 times" in error for error in errors)


def test_required_turn_evidence_inside_the_recent_window_is_reported() -> None:
    campaign = make_campaign()
    errors = validate_campaign(with_probe(campaign, _probe(at_turn=5)))
    assert any("inside the recent window" in error for error in errors)
    assert not any(
        "inside the recent window" in error
        for error in validate_campaign(with_probe(campaign, _probe(at_turn=7)))
    )


def test_negated_plant_may_be_required_and_forbidden_but_needs_a_claim() -> None:
    campaign = make_campaign()
    good = PlantDef(
        plant_id="pl_neg",
        source="turn",
        turn=2,
        kind="negated",
        anchor_text="grows a second head",
        subject_key="vale",
        predicate="has",
        object_literal="two heads",
    )
    probe = _probe(
        failure_class="negation_conditional", required=["pl_neg"], forbidden=["pl_neg"]
    )
    with_plant = replace(campaign, plants=[*campaign.plants, good])
    assert validate_campaign(with_probe(with_plant, probe)) == []
    bare = good.model_copy(update={"subject_key": None})
    errors = validate_campaign(
        with_probe(replace(campaign, plants=[*campaign.plants, bare]), probe)
    )
    assert any("needs the denied claim" in error for error in errors)


def test_plant_sheet_lists_every_probe_with_its_anchors() -> None:
    from eval.plant_sheet import build_sheet

    sheet = build_sheet([make_campaign()])
    assert "`pr1`" in sheet and "swears to guard the ferry" in sheet
    rows = [line for line in sheet.splitlines() if line.startswith("| `")]
    assert len(rows) == len(make_campaign().probes)


def test_a_distractor_may_not_also_be_required() -> None:
    probe = _probe(distractors=["pl_oath"], style="vague")
    errors = validate_campaign(with_probe(make_campaign(), probe))
    assert any("distractor is also required or forbidden" in error for error in errors)


def _write_campaign(root: Path, campaign) -> None:
    directory = root / campaign.campaign_id
    directory.mkdir(parents=True)
    (directory / "scenario.json").write_text(
        campaign.scenario.model_dump_json(), encoding="utf-8"
    )
    for name, items in (
        ("turns.jsonl", campaign.turns),
        ("decoy.jsonl", campaign.decoy_turns),
        ("plants.jsonl", campaign.plants),
        ("probes.jsonl", campaign.probes),
    ):
        (directory / name).write_text(
            "\n".join(i.model_dump_json() for i in items) + "\n", encoding="utf-8"
        )


def test_freeze_blocks_a_run_after_the_corpus_is_edited(tmp_path: Path) -> None:
    from eval.errors import HarnessError
    from eval.freeze import check_frozen, write_freeze

    _write_campaign(tmp_path, make_campaign())
    campaign = load_campaign(tmp_path / "T1")
    check_frozen(tmp_path, [campaign])
    with pytest.raises(HarnessError):
        write_freeze(tmp_path, "2")
    unfrozen_hash = campaign.content_hash
    record = {
        "version": "2",
        "frozen_on": "2026-10-27",
        "content_hashes": {"T1": unfrozen_hash},
        "probe_counts": {"T1": 1},
    }
    (tmp_path / "FREEZE.json").write_text(json.dumps(record), encoding="utf-8")
    check_frozen(tmp_path, [campaign])
    (tmp_path / "T1" / "turns.jsonl").write_text("changed\n", encoding="utf-8")
    edited = replace(campaign, content_hash="different")
    with pytest.raises(HarnessError):
        check_frozen(tmp_path, [edited])
