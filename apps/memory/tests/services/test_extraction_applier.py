"""apply_plan against real Postgres: entities, facts, supersessions, commitments, scene."""

from uuid import UUID

from app.models.extraction import (
    CommitmentUpdate,
    ExtractedFact,
    NewCommitment,
    NewEntity,
    SceneClaim,
    SupersessionClaim,
    ValidatedPlan,
)
from app.models.facts import EntityCreate, FactCreate
from app.models.jobs import ExtractionBatchCreate, ExtractionBatchRow
from app.repositories import (
    commitment_repo,
    entity_repo,
    extraction_batch_repo,
    fact_repo,
    scene_repo,
    span_repo,
)
from app.services.extraction_applier import ApplyInput, apply_plan
from psycopg import AsyncConnection
from tests.repositories.helpers_evidence import (
    build_span,
    make_playthrough,
    make_source,
)

LABEL_FIRST = "S3.1"
LABEL_LAST = "S4.1"


async def _entity(connection: AsyncConnection, scope_id: UUID, name: str) -> UUID:
    row = await entity_repo.create_entity(
        connection,
        EntityCreate(
            scope_kind="playthrough",
            scope_id=scope_id,
            entity_type="Character",
            canonical_name=name,
            provenance="authored",
            first_seen_seq=0,
        ),
    )
    return row.entity_id


async def _batch(connection: AsyncConnection, scope_id: UUID) -> ExtractionBatchRow:
    return await extraction_batch_repo.create_batch(
        connection,
        ExtractionBatchCreate(
            scope_kind="playthrough",
            scope_id=scope_id,
            from_seq=3,
            to_seq=4,
            status="pending",
            model="m",
            prompt_version="extraction_v1",
            input_hash="h",
        ),
    )


async def _spans(connection: AsyncConnection, scope_id: UUID) -> dict[str, object]:
    spans = {}
    for sequence, label in ((3, LABEL_FIRST), (4, LABEL_LAST)):
        source = await make_source(
            connection,
            scope_kind="playthrough",
            scope_id=scope_id,
            source_kind="turn_narration",
            source_ref=f"turn-{sequence}",
            sequence=sequence,
        )
        rows = await span_repo.create_spans(
            connection,
            [
                build_span(
                    source_id=source.source_id,
                    scope_kind="playthrough",
                    scope_id=scope_id,
                    sequence=sequence,
                    label=label,
                )
            ],
        )
        spans[label] = rows[0]
    return spans


async def _input(
    connection: AsyncConnection, plan: ValidatedPlan, scope_id: UUID
) -> ApplyInput:
    return ApplyInput(
        batch=await _batch(connection, scope_id),
        plan=plan,
        spans_by_label=await _spans(connection, scope_id),  # type: ignore[arg-type]
    )


async def test_new_entity_and_fact_are_written_with_sources_and_extracted_authority(
    db_connection: AsyncConnection,
) -> None:
    playthrough = await make_playthrough(db_connection)
    scope_id = playthrough.playthrough_id
    known = await _entity(db_connection, scope_id, "Captain Vale")
    plan = ValidatedPlan(
        new_entities=[
            NewEntity(
                temp_key="t1",
                entity_type="Character",
                name="Old Marta",
                aliases=["Marta"],
                evidence=[LABEL_FIRST],
            )
        ],
        facts=[
            ExtractedFact(
                subject="t1",
                predicate="serves",
                object=str(known),
                object_literal=None,
                assertion="occurred",
                speaker=None,
                evidence=[LABEL_FIRST, LABEL_LAST],
            )
        ],
    )
    apply_input = await _input(db_connection, plan, scope_id)

    applied = await apply_plan(db_connection, apply_input)

    assert applied == 2
    found = await entity_repo.find_entities_by_alias(
        db_connection, [("playthrough", scope_id)], ["old marta", "marta"]
    )
    assert {match[1].provenance for match in found} == {"extracted"}
    facts = await fact_repo.list_valid_facts_at(db_connection, scope_id, None, 10)
    assert [fact.authority for fact in facts] == ["extracted"]
    assert facts[0].valid_from_seq == 4
    assert facts[0].object_entity_id == known
    assert facts[0].extraction_batch_id == apply_input.batch.batch_id


async def test_reused_entity_is_referenced_without_creating_a_new_one(
    db_connection: AsyncConnection,
) -> None:
    playthrough = await make_playthrough(db_connection)
    scope_id = playthrough.playthrough_id
    existing = await _entity(db_connection, scope_id, "Old Marta")
    other = await _entity(db_connection, scope_id, "Captain Vale")
    plan = ValidatedPlan(
        reused_entities={"t1": str(existing)},
        facts=[
            ExtractedFact(
                subject="t1",
                predicate="serves",
                object=str(other),
                object_literal=None,
                assertion="occurred",
                speaker=None,
                evidence=[LABEL_FIRST],
            )
        ],
    )

    applied = await apply_plan(
        db_connection, await _input(db_connection, plan, scope_id)
    )

    assert applied == 1
    facts = await fact_repo.list_valid_facts_at(db_connection, scope_id, None, 10)
    assert facts[0].subject_entity_id == existing


async def test_commitment_status_supersession_and_scene_are_written(
    db_connection: AsyncConnection,
) -> None:
    playthrough = await make_playthrough(db_connection)
    scope_id = playthrough.playthrough_id
    owner = await _entity(db_connection, scope_id, "Captain Vale")
    place = await _entity(db_connection, scope_id, "Harbour")
    old_fact = (
        await fact_repo.create_facts(
            db_connection,
            [
                FactCreate(
                    scope_kind="playthrough",
                    scope_id=scope_id,
                    subject_entity_id=owner,
                    predicate="is_alive",
                    object_literal="true",
                    authority="extracted",
                    assertion="occurred",
                    valid_from_seq=1,
                )
            ],
        )
    )[0]
    plan = ValidatedPlan(
        supersessions=[
            SupersessionClaim(
                fact_id=str(old_fact.fact_id), evidence=[LABEL_LAST], reason="died"
            )
        ],
        new_commitments=[
            NewCommitment(
                kind="promise",
                owner=str(owner),
                counterparty=None,
                summary="Return the ring",
                evidence=[LABEL_FIRST],
            )
        ],
        scene=SceneClaim(
            location=str(place), present=[str(owner)], evidence=[LABEL_LAST]
        ),
    )
    apply_input = await _input(db_connection, plan, scope_id)

    applied = await apply_plan(db_connection, apply_input)

    assert applied == 3
    scene = await scene_repo.get_scene_at(db_connection, scope_id, 10)
    assert scene is not None and scene.location_entity_id == place
    assert scene.present_entity_ids == [owner]
    commitments = await commitment_repo.list_commitments_at(db_connection, scope_id, 10)
    assert [entry[0].summary for entry in commitments] == ["Return the ring"]
    valid = await fact_repo.list_valid_facts_at(db_connection, scope_id, None, 10)
    assert old_fact.fact_id not in {fact.fact_id for fact in valid}


async def test_commitment_update_appends_a_status_at_the_evidence_sequence(
    db_connection: AsyncConnection,
) -> None:
    playthrough = await make_playthrough(db_connection)
    scope_id = playthrough.playthrough_id
    owner = await _entity(db_connection, scope_id, "Captain Vale")
    opening = ValidatedPlan(
        new_commitments=[
            NewCommitment(
                kind="quest",
                owner=str(owner),
                counterparty=None,
                summary="Find the key",
                evidence=[LABEL_FIRST],
            )
        ]
    )
    apply_input = await _input(db_connection, opening, scope_id)
    await apply_plan(db_connection, apply_input)
    commitment = (
        await commitment_repo.list_commitments_at(db_connection, scope_id, 10)
    )[0][0]
    closing = ValidatedPlan(
        commitment_updates=[
            CommitmentUpdate(
                commitment_id=str(commitment.commitment_id),
                status="fulfilled",
                evidence=[LABEL_LAST],
            )
        ]
    )

    await apply_plan(
        db_connection,
        ApplyInput(apply_input.batch, closing, apply_input.spans_by_label),
    )

    latest = (await commitment_repo.list_commitments_at(db_connection, scope_id, 10))[
        0
    ][1]
    assert latest is not None and latest.status == "fulfilled" and latest.at_seq == 4


async def test_empty_plan_writes_nothing(db_connection: AsyncConnection) -> None:
    playthrough = await make_playthrough(db_connection)

    applied = await apply_plan(
        db_connection,
        await _input(db_connection, ValidatedPlan(), playthrough.playthrough_id),
    )

    assert applied == 0
