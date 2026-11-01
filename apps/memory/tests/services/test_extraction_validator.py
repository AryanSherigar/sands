"""Pure validation of extraction output against a ValidationContext."""

from uuid import uuid4

from app.models.extraction import (
    CommitmentUpdate,
    ExtractedFact,
    ExtractionOutput,
    NewCommitment,
    NewEntity,
    SceneClaim,
    SupersessionClaim,
)
from app.services.extraction_validator import (
    RejectedTarget,
    ValidationContext,
    normalize_predicate,
    validate_output,
)

LABEL = "S3.1"
OUTSIDE_LABEL = "S99.1"
ROSTER_ID = str(uuid4())
OTHER_ROSTER_ID = str(uuid4())
FACT_ID = str(uuid4())
ACCEPTED_FACT_ID = str(uuid4())
COMMITMENT_ID = str(uuid4())
EXTRACTED_ENTITY_ID = str(uuid4())


def _context(**overrides: object) -> ValidationContext:
    base: dict[str, object] = {
        "batch_labels": frozenset({LABEL, "S3.2"}),
        "roster_entity_ids": frozenset({ROSTER_ID, OTHER_ROSTER_ID}),
        "supersedable_fact_ids": frozenset({FACT_ID}),
        "open_commitment_ids": frozenset({COMMITMENT_ID}),
        "tracked_predicates": frozenset(),
        "rejected_targets": frozenset(),
    }
    base.update(overrides)
    return ValidationContext(**base)  # type: ignore[arg-type]


def _output(**overrides: object) -> ExtractionOutput:
    base: dict[str, object] = {
        "new_entities": [],
        "facts": [],
        "supersessions": [],
        "new_commitments": [],
        "commitment_updates": [],
        "scene": None,
    }
    base.update(overrides)
    return ExtractionOutput(**base)  # type: ignore[arg-type]


def _fact(**overrides: object) -> ExtractedFact:
    base: dict[str, object] = {
        "subject": ROSTER_ID,
        "predicate": "Allied With",
        "object": OTHER_ROSTER_ID,
        "object_literal": None,
        "assertion": "occurred",
        "speaker": None,
        "evidence": [LABEL],
    }
    base.update(overrides)
    return ExtractedFact(**base)  # type: ignore[arg-type]


def _entity(
    temp_key: str = "t1", name: str = "Old Marta", **overrides: object
) -> NewEntity:
    base: dict[str, object] = {
        "temp_key": temp_key,
        "entity_type": "Character",
        "name": name,
        "aliases": [],
        "evidence": [LABEL],
    }
    base.update(overrides)
    return NewEntity(**base)  # type: ignore[arg-type]


def test_normalize_predicate_snake_cases() -> None:
    assert normalize_predicate("  Allied-With!! ") == "allied_with"


def test_valid_fact_is_kept_with_normalized_predicate() -> None:
    plan = validate_output(_output(facts=[_fact()]), _context())

    assert [fact.predicate for fact in plan.facts] == ["allied_with"]
    assert plan.dropped == {}


def test_fact_with_unknown_subject_id_is_dropped() -> None:
    plan = validate_output(_output(facts=[_fact(subject=str(uuid4()))]), _context())

    assert plan.facts == []
    assert plan.dropped == {"unknown_id": 1}


def test_injected_identity_instruction_cannot_produce_an_id_outside_the_roster() -> (
    None
):
    forged = str(uuid4())

    plan = validate_output(
        _output(
            facts=[_fact(object=forged)],
            scene=SceneClaim(location=forged, present=[forged], evidence=[LABEL]),
        ),
        _context(),
    )

    assert plan.facts == []
    assert plan.scene is None


def test_evidence_outside_the_batch_is_filtered_and_empty_evidence_drops_the_item() -> (
    None
):
    kept = validate_output(
        _output(facts=[_fact(evidence=[LABEL, OUTSIDE_LABEL])]), _context()
    )
    dropped = validate_output(
        _output(facts=[_fact(evidence=[OUTSIDE_LABEL])]), _context()
    )

    assert kept.facts[0].evidence == [LABEL]
    assert dropped.facts == []
    assert dropped.dropped == {"bad_evidence": 1}


def test_fact_without_object_or_literal_is_dropped() -> None:
    plan = validate_output(
        _output(facts=[_fact(object=None, object_literal="  ")]), _context()
    )

    assert plan.facts == []
    assert plan.dropped == {"empty_field": 1}


def test_literal_fact_is_kept() -> None:
    plan = validate_output(
        _output(facts=[_fact(object=None, object_literal="the north gate")]), _context()
    )

    assert len(plan.facts) == 1


def test_master_tracked_predicate_is_dropped() -> None:
    plan = validate_output(
        _output(facts=[_fact(predicate="Health", object=None, object_literal="3")]),
        _context(tracked_predicates=frozenset({"health"})),
    )

    assert plan.facts == []
    assert plan.dropped == {"tracked_field": 1}


def test_occurred_fact_matching_a_rejected_mutation_is_dropped() -> None:
    context = _context(rejected_targets=frozenset({RejectedTarget(ROSTER_ID, "gold")}))

    plan = validate_output(
        _output(facts=[_fact(predicate="gold", object=None, object_literal="50")]),
        context,
    )

    assert plan.facts == []
    assert plan.dropped == {"rejected_mutation": 1}


def test_stated_claim_about_a_rejected_target_is_kept_as_a_claim() -> None:
    context = _context(rejected_targets=frozenset({RejectedTarget(ROSTER_ID, "gold")}))

    plan = validate_output(
        _output(
            facts=[
                _fact(
                    predicate="gold",
                    object=None,
                    object_literal="50",
                    assertion="stated",
                    speaker=OTHER_ROSTER_ID,
                )
            ]
        ),
        context,
    )

    assert len(plan.facts) == 1


def test_duplicate_facts_collapse() -> None:
    plan = validate_output(_output(facts=[_fact(), _fact()]), _context())

    assert len(plan.facts) == 1
    assert plan.dropped == {"duplicate": 1}


def test_temp_key_resolves_for_facts_about_a_new_entity() -> None:
    plan = validate_output(
        _output(new_entities=[_entity()], facts=[_fact(subject="t1")]), _context()
    )

    assert [entity.temp_key for entity in plan.new_entities] == ["t1"]
    assert len(plan.facts) == 1


def test_fact_about_a_dropped_new_entity_is_dropped() -> None:
    plan = validate_output(
        _output(
            new_entities=[_entity(evidence=[OUTSIDE_LABEL])],
            facts=[_fact(subject="t1")],
        ),
        _context(),
    )

    assert plan.new_entities == []
    assert plan.facts == []


def test_exact_match_to_one_extracted_entity_is_reused() -> None:
    context = _context(extracted_aliases={"old marta": [EXTRACTED_ENTITY_ID]})

    plan = validate_output(
        _output(new_entities=[_entity()], facts=[_fact(subject="t1")]), context
    )

    assert plan.new_entities == []
    assert plan.reused_entities == {"t1": EXTRACTED_ENTITY_ID}
    assert len(plan.facts) == 1


def test_match_to_two_extracted_entities_is_left_unlinked_as_a_new_entity() -> None:
    context = _context(
        extracted_aliases={"old marta": [EXTRACTED_ENTITY_ID, str(uuid4())]}
    )

    plan = validate_output(_output(new_entities=[_entity()]), context)

    assert [entity.temp_key for entity in plan.new_entities] == ["t1"]
    assert plan.reused_entities == {}


def test_name_matching_an_authored_entity_is_never_merged() -> None:
    context = _context(
        authored_aliases=frozenset({"old marta"}),
        extracted_aliases={"old marta": [EXTRACTED_ENTITY_ID]},
    )

    plan = validate_output(_output(new_entities=[_entity()]), context)

    assert plan.reused_entities == {}
    assert [entity.temp_key for entity in plan.new_entities] == ["t1"]
    assert plan.dropped == {"authored_name_collision": 1}


def test_duplicate_temp_keys_keep_the_first_only() -> None:
    plan = validate_output(
        _output(new_entities=[_entity(), _entity(name="Someone Else")]), _context()
    )

    assert len(plan.new_entities) == 1


def test_supersession_of_a_supersedable_fact_is_kept() -> None:
    plan = validate_output(
        _output(
            supersessions=[
                SupersessionClaim(fact_id=FACT_ID, evidence=[LABEL], reason="died")
            ]
        ),
        _context(),
    )

    assert len(plan.supersessions) == 1


def test_supersession_of_an_accepted_or_unknown_fact_is_dropped() -> None:
    claims = [
        SupersessionClaim(fact_id=ACCEPTED_FACT_ID, evidence=[LABEL], reason="x"),
        SupersessionClaim(fact_id=str(uuid4()), evidence=[LABEL], reason="x"),
    ]

    plan = validate_output(_output(supersessions=claims), _context())

    assert plan.supersessions == []
    assert plan.dropped == {"not_supersedable": 2}


def test_commitment_with_unknown_counterparty_is_kept_without_it() -> None:
    commitment = NewCommitment(
        kind="promise",
        owner=ROSTER_ID,
        counterparty=str(uuid4()),
        summary="Return the ring",
        evidence=[LABEL],
    )

    plan = validate_output(_output(new_commitments=[commitment]), _context())

    assert plan.new_commitments[0].counterparty is None


def test_commitment_with_unknown_owner_is_dropped() -> None:
    commitment = NewCommitment(
        kind="debt",
        owner=str(uuid4()),
        counterparty=None,
        summary="x",
        evidence=[LABEL],
    )

    plan = validate_output(_output(new_commitments=[commitment]), _context())

    assert plan.new_commitments == []


def test_commitment_update_requires_an_open_listed_commitment() -> None:
    updates = [
        CommitmentUpdate(
            commitment_id=COMMITMENT_ID, status="fulfilled", evidence=[LABEL]
        ),
        CommitmentUpdate(commitment_id=str(uuid4()), status="broken", evidence=[LABEL]),
    ]

    plan = validate_output(_output(commitment_updates=updates), _context())

    assert [update.commitment_id for update in plan.commitment_updates] == [
        COMMITMENT_ID
    ]


def test_scene_keeps_only_known_entities() -> None:
    scene = SceneClaim(
        location=ROSTER_ID, present=[OTHER_ROSTER_ID, str(uuid4())], evidence=[LABEL]
    )

    plan = validate_output(_output(scene=scene), _context())

    assert plan.scene is not None
    assert plan.scene.present == [OTHER_ROSTER_ID]


def test_empty_output_yields_empty_plan() -> None:
    plan = validate_output(_output(), _context())

    assert plan.model_dump(exclude={"dropped"}) == {
        "new_entities": [],
        "reused_entities": {},
        "facts": [],
        "supersessions": [],
        "new_commitments": [],
        "commitment_updates": [],
        "scene": None,
    }


def test_template_scope_ignores_supersessions_commitments_and_scene() -> None:
    commitment = NewCommitment(
        kind="quest", owner=ROSTER_ID, counterparty=None, summary="x", evidence=[LABEL]
    )
    scene = SceneClaim(location=ROSTER_ID, present=[], evidence=[LABEL])

    plan = validate_output(
        _output(facts=[_fact()], new_commitments=[commitment], scene=scene),
        _context(is_template_scope=True),
    )

    assert len(plan.facts) == 1
    assert plan.new_commitments == []
    assert plan.scene is None
    assert plan.dropped == {"template_scope_item": 2}


def test_occurred_fact_with_a_negation_in_its_predicate_is_dropped_only_when_enabled() -> (
    None
):
    negated = _fact(predicate="Has Not Paid", object=None, object_literal="the toll")

    kept = validate_output(_output(facts=[negated]), _context())
    dropped = validate_output(
        _output(facts=[negated]), _context(is_negated_predicate_rejected=True)
    )

    assert len(kept.facts) == 1
    assert dropped.facts == []
    assert dropped.dropped == {"negated_predicate": 1}


def test_stated_claims_and_ordinary_predicates_survive_the_negation_rule() -> None:
    context = _context(is_negated_predicate_rejected=True)
    stated = _fact(
        predicate="did_not_pay",
        object=None,
        object_literal="the toll",
        assertion="stated",
        speaker=OTHER_ROSTER_ID,
    )
    ordinary = _fact(predicate="knotted_rope", object=None, object_literal="a rope")

    plan = validate_output(_output(facts=[stated, ordinary]), context)

    assert len(plan.facts) == 2
