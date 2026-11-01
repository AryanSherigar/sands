from uuid import uuid4

from app.models.extraction import (
    CommitmentUpdate,
    ExtractedFact,
    NewCommitment,
    NewEntity,
    SupersessionClaim,
    ValidatedPlan,
)
from app.models.facts import EntityRow
from eval.extraction_observe import (
    build_entity_key_map,
    build_name_index,
    evidence_turns,
    observe_plans,
)
from eval.keys import key_uuid
from eval.labels import ExtractionLabel
from eval.scoring.extraction import (
    ExtractionObservation,
    ObservedCommitment,
    ObservedEntity,
    ObservedFact,
    duplicate_entity_rate,
    score_extraction,
)
from tests.evaluation.campaign_helpers import make_campaign


def _fact(turn: int = 5, **overrides: object) -> ObservedFact:
    values: dict[str, object] = {
        "turns": frozenset({turn}),
        "subject_key": "mira",
        "predicate": "guards",
        "object_key": None,
        "object_text": "the ferry at dawn",
        "assertion": "occurred",
    }
    values.update(overrides)
    return ObservedFact(**values)


def _label(**overrides: object) -> ExtractionLabel:
    values: dict[str, object] = {
        "label_id": "l1",
        "label_type": "fact",
        "turn": 5,
        "anchor_text": "Mira guards the ferry at dawn",
        "subject_key": "mira",
        "object_literal": "ferry at dawn",
    }
    values.update(overrides)
    return ExtractionLabel.model_validate(values)


def _score(labels: list[ExtractionLabel], **observation: object):
    return score_extraction(labels, ExtractionObservation(**observation), {"mira"})


def test_fact_hit_by_literal_overlap_and_subject() -> None:
    score = _score([_label(), _label(label_id="l2")], facts=[_fact()])
    assert score.by_type["fact"].recall_hits == 2


def test_fact_miss_on_wrong_turn_or_subject() -> None:
    score = _score([_label()], facts=[_fact(turn=6), _fact(subject_key="vale")])
    assert score.by_type["fact"].recall_hits == 0


def test_fact_hit_by_object_entity_key() -> None:
    label = _label(object_key="ferry", object_literal=None)
    assert (
        _score([label], facts=[_fact(object_key="ferry")]).by_type["fact"].recall_hits
        == 1
    )
    assert (
        _score([label], facts=[_fact(object_key="inn")]).by_type["fact"].recall_hits
        == 0
    )


def test_precision_only_counts_facts_at_labeled_turns() -> None:
    facts = [_fact(), _fact(turn=40, predicate="loves", object_text="cats")]
    score = _score([_label(), _label(label_id="l2")], facts=facts)
    assert score.by_type["fact"].predicted_count == 1


def test_commitment_open_and_update_with_wrong_status() -> None:
    labels = [
        _label(
            label_id="c1",
            label_type="commitment",
            turn=2,
            subject_key="mira",
            status="open",
        ),
        _label(
            label_id="c2",
            label_type="commitment",
            turn=9,
            status="fulfilled",
            supersedes_label_id="c1",
        ),
    ]
    items = [
        ObservedCommitment(frozenset({2}), "mira", "promise", "open", False),
        ObservedCommitment(frozenset({9}), None, None, "broken", True),
    ]
    score = _score(labels, commitments=items)
    commitments = score.by_type["commitment"]
    assert commitments.recall_hits == 2 and commitments.wrong_status == 1


def test_supersession_recall_and_precision() -> None:
    labels = [_label(label_id="s1", label_type="supersession", turn=7)]
    score = _score(labels, supersession_turns=[frozenset({7}), frozenset({30})])
    assert score.by_type["supersession"].recall_hits == 1
    assert score.by_type["supersession"].predicted_count == 2


def test_entity_link_hit_needs_matching_turn_and_key() -> None:
    labels = [
        _label(label_id="e1", label_type="entity_link", turn=4, subject_key="vale")
    ]
    assert (
        _score(labels, mentions=[(frozenset({4}), "vale")])
        .by_type["entity_link"]
        .recall_hits
        == 1
    )
    assert (
        _score(labels, mentions=[(frozenset({4}), "mira")])
        .by_type["entity_link"]
        .recall_hits
        == 0
    )


def test_forbidden_counts_only_occurred_claims_at_the_rejected_turn() -> None:
    label = _label(
        label_id="f1",
        label_type="forbidden_fact",
        turn=3,
        anchor_text="the arm grows a second head",
        subject_key=None,
        object_literal=None,
    )
    bad = _fact(turn=3, predicate="grows", object_text="second head")
    safe = _fact(
        turn=3, predicate="grows", object_text="second head", assertion="attempted"
    )
    assert _score([label], facts=[bad]).forbidden_extracted == 1
    assert _score([label], facts=[safe]).forbidden_extracted == 0


def test_duplicate_entity_rate_counts_repeats_of_known_keys() -> None:
    entities = [
        ObservedEntity("Mira", "mira"),
        ObservedEntity("The Hag", "hag"),
        ObservedEntity("Hag", "hag"),
    ]
    assert duplicate_entity_rate(entities, {"mira"}) == 2 / 3
    assert duplicate_entity_rate([], {"mira"}) == 0.0


def test_evidence_turns_parse_span_labels() -> None:
    assert evidence_turns(["S12.3", "S12.1", "S40.2", "bogus"]) == frozenset({12, 40})


def _plan(**overrides: object) -> ValidatedPlan:
    return ValidatedPlan(**overrides)


def _row(name: str, authored: object = None) -> EntityRow:
    return EntityRow(
        scope_kind="playthrough",
        scope_id=uuid4(),
        authored_entity_id=authored,
        entity_type="character",
        canonical_name=name,
        provenance="authored" if authored else "extracted",
        first_seen_seq=0,
        entity_id=uuid4(),
    )


def test_key_map_resolves_authored_ids_names_and_aliases() -> None:
    campaign = make_campaign()
    authored = _row("Mira", key_uuid("T1", "mira"))
    by_name = _row("captain vale")
    unknown = _row("Stranger")
    key_map = build_entity_key_map([authored, by_name, unknown], [], campaign)
    assert key_map[str(authored.entity_id)] == "mira"
    assert key_map[str(by_name.entity_id)] == "vale"
    assert key_map[str(unknown.entity_id)] is None


def test_observe_plans_resolves_temp_keys_reused_entities_and_turns() -> None:
    campaign = make_campaign()
    names = build_name_index(campaign)
    mira = _row("Mira", key_uuid("T1", "mira"))
    key_map = build_entity_key_map([mira], [], campaign)
    plan = _plan(
        new_entities=[
            NewEntity(
                temp_key="t1",
                entity_type="character",
                name="Captain Vale",
                aliases=[],
                evidence=["S2.1"],
            )
        ],
        facts=[
            ExtractedFact(
                subject=str(mira.entity_id),
                predicate="serves",
                object="t1",
                object_literal=None,
                assertion="occurred",
                speaker=None,
                evidence=["S2.1"],
            )
        ],
        new_commitments=[
            NewCommitment(
                kind="promise",
                owner=str(mira.entity_id),
                counterparty=None,
                summary="x",
                evidence=["S3.1"],
            )
        ],
        commitment_updates=[
            CommitmentUpdate(commitment_id="c", status="fulfilled", evidence=["S9.1"])
        ],
        supersessions=[SupersessionClaim(fact_id="f", evidence=["S7.2"], reason="r")],
    )
    observation = observe_plans([plan], key_map, names)
    assert (
        observation.facts[0].subject_key == "mira"
        and observation.facts[0].object_key == "vale"
    )
    assert (
        observation.commitments[0].owner_key == "mira"
        and observation.commitments[1].is_update
    )
    assert observation.supersession_turns == [frozenset({7})]
    assert observation.new_entities[0].key == "vale"


def test_fact_objects_resolve_to_entity_names_not_ids_or_temp_keys() -> None:
    campaign = make_campaign()
    mira = _row("Mira", key_uuid("T1", "mira"))
    vale = _row("Captain Vale")
    key_map = build_entity_key_map([mira, vale], [], campaign)
    display = {str(mira.entity_id): "Mira", str(vale.entity_id): "Captain Vale"}
    facts = [
        ExtractedFact(
            subject=str(mira.entity_id),
            predicate="serves",
            object="t1",
            object_literal=None,
            assertion="occurred",
            speaker=None,
            evidence=["S2.1"],
        ),
        ExtractedFact(
            subject=str(mira.entity_id),
            predicate="knows",
            object=str(vale.entity_id),
            object_literal=None,
            assertion="occurred",
            speaker=None,
            evidence=["S2.1"],
        ),
    ]
    plan = _plan(
        new_entities=[
            NewEntity(
                temp_key="t1",
                entity_type="location",
                name="Ember Inn",
                aliases=[],
                evidence=["S2.1"],
            )
        ],
        facts=facts,
    )
    observation = observe_plans([plan], key_map, build_name_index(campaign), display)
    assert [fact.object_text for fact in observation.facts] == [
        "Ember Inn",
        "Captain Vale",
    ]


def test_master_authors_every_entity_and_newbie_only_the_registered_player() -> None:
    from dataclasses import replace

    from eval.runner import authored_entity_keys

    master = make_campaign()
    assert authored_entity_keys(master) == {"mira", "vale"}
    newbie = replace(
        master, scenario=master.scenario.model_copy(update={"mode": "newbie"})
    )
    assert authored_entity_keys(newbie) == {"mira"}


def test_negated_fact_count_flags_negations_written_into_the_predicate() -> None:
    from eval.scoring.extraction import ObservedFact, negated_fact_count

    def fact(predicate: str, assertion: str = "occurred") -> ObservedFact:
        return ObservedFact(frozenset({3}), "wren", predicate, None, "gold", assertion)

    facts = [
        fact("has_not_paid"),
        fact("does_not_pay"),
        fact("carries"),
        fact("has_not_paid", "stated"),
    ]
    assert negated_fact_count(facts) == 2
