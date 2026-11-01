"""State-change fixture set: case validation, scoring and an end-to-end seeded run."""

import time
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
import respx
from app.integrations.extraction_queue import ExtractionQueue
from app.repositories import span_repo
from eval.errors import HarnessError
from eval.scoring.statechange import (
    CaseOutcome,
    ObservedText,
    covers,
    score_case,
    summarize_by_category,
)
from eval.statechange_cases import CASES_FILE, StateChangeCase, load_cases
from eval.statechange_run import collect_outcome
from eval.statechange_seed import seed_case
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool
from pydantic import ValidationError
from tests.services.extraction_helpers import (
    EMPTY_OUTPUT,
    TRUNCATE_QUEUE,
    build_service,
    extraction_ok,
    make_settings,
    mock_extraction,
)

DEADLINE_SECONDS = 60


def _case(**overrides: object) -> StateChangeCase:
    body: dict[str, object] = {
        "case_id": "chg_test",
        "category": "change",
        "note": "Pip moves out of the inn",
        "entities": [{"key": "pip", "name": "Pip", "aliases": ["the lodger"]}],
        "prior_facts": [
            {
                "key": "old",
                "subject": "pip",
                "predicate": "lodges_at",
                "object_literal": "the Wet Rope inn",
            },
            {
                "key": "other",
                "subject": "pip",
                "predicate": "carries",
                "object_literal": "a copper lantern",
            },
        ],
        "turns": [
            {
                "action": "I ask where Pip sleeps.",
                "narration": "Pip says he now lodges in the Brasswrights attic.",
            }
        ],
        "expect": {
            "superseded": ["old"],
            "kept": ["other"],
            "required": [{"subject": "pip", "words": ["brasswrights", "attic"]}],
            "forbidden": [{"words": ["wet", "rope", "inn"]}],
        },
    }
    return StateChangeCase.model_validate({**body, **overrides})


def test_the_shipped_case_file_loads_when_present() -> None:
    if not CASES_FILE.exists():
        pytest.skip("cases.jsonl not authored yet")
    cases = load_cases()
    assert len({case.case_id for case in cases}) == len(cases)


def test_a_case_cannot_reference_an_unknown_fact_key() -> None:
    with pytest.raises(ValidationError, match="unknown fact key"):
        _case(expect={"superseded": ["missing"]})


def test_a_fact_cannot_be_both_superseded_and_kept() -> None:
    with pytest.raises(ValidationError, match="both superseded and kept"):
        _case(expect={"superseded": ["old"], "kept": ["old"]})


def test_a_case_is_limited_to_one_batch_of_turns() -> None:
    turn = {"action": "I wait.", "narration": "Nothing."}
    with pytest.raises(ValidationError):
        _case(turns=[turn] * 6)


def test_duplicate_case_ids_are_rejected(tmp_path: Path) -> None:
    line = _case().model_dump_json()
    path = tmp_path / "cases.jsonl"
    path.write_text(f"{line}\n{line}\n", encoding="utf-8")
    with pytest.raises(HarnessError):
        load_cases(path)


def test_covers_needs_most_of_the_words() -> None:
    assert covers(["brasswrights", "attic"], "lodges at the Brasswrights' attic")
    assert not covers(["brasswrights", "attic"], "lodges at the inn")


def _fact(
    text: str, predicate: str = "lodges_at", assertion: str = "occurred"
) -> ObservedText:
    return ObservedText("pip", predicate, text, assertion)


def test_a_correct_change_scores_full_recall_and_no_false_supersession() -> None:
    outcome = CaseOutcome(
        frozenset({"old"}), [_fact("lodges at the Brasswrights attic")]
    )

    score = score_case(_case(), outcome)

    assert (score.retired_hits, score.wrongly_retired) == (1, 0)
    assert (score.required_hits, score.leaks) == (1, 0)


def test_a_wrongly_retired_fact_and_a_stale_leak_are_counted() -> None:
    outcome = CaseOutcome(
        frozenset({"old", "other"}),
        [_fact("lodges at the Wet Rope inn", predicate="does_not_lodge_at")],
    )

    score = score_case(_case(), outcome)

    assert score.wrongly_retired == 1
    assert score.leaks == 1
    assert score.negated == 1
    assert score.required_hits == 0


def test_a_claim_that_was_only_stated_is_not_a_leak() -> None:
    outcome = CaseOutcome(
        frozenset(), [_fact("lodges at the Wet Rope inn", assertion="stated")]
    )

    assert score_case(_case(), outcome).leaks == 0


def test_summaries_pool_by_category_with_an_overall_row() -> None:
    hit = score_case(_case(), CaseOutcome(frozenset({"old"}), []))
    miss = score_case(_case(case_id="chg_two"), CaseOutcome(frozenset(), []))

    summary = summarize_by_category([hit, miss])

    assert summary["change"].supersession_recall == 0.5
    assert summary["overall"].cases == 2


@pytest.fixture
async def queue(retrieval_pool: AsyncConnectionPool) -> AsyncIterator[ExtractionQueue]:
    async with retrieval_pool.connection() as connection:
        await connection.execute(TRUNCATE_QUEUE)
    extraction_queue = ExtractionQueue(2, 1)
    await extraction_queue.open(retrieval_pool)
    yield extraction_queue
    await extraction_queue.close()


@pytest.fixture
async def retrieval_pool(
    migrated_test_database_url: str, db_connection: AsyncConnection
) -> AsyncIterator[AsyncConnectionPool]:
    pool = AsyncConnectionPool(migrated_test_database_url, max_size=4, open=False)
    await pool.open()
    yield pool
    await pool.close()


@pytest.fixture
def model_api() -> Iterator[respx.MockRouter]:
    with respx.mock(assert_all_called=False) as router:
        yield router


async def test_a_seeded_case_runs_through_extraction_and_is_scored(
    db_connection: AsyncConnection,
    retrieval_pool: AsyncConnectionPool,
    queue: ExtractionQueue,
    model_api: respx.MockRouter,
) -> None:
    case = _case()
    seeded = await seed_case(db_connection, case)
    spans = await span_repo.list_spans_by_sequence(
        db_connection, "playthrough", seeded.playthrough_id, 1, 1
    )
    new_fact = {
        "subject": str(seeded.entity_ids["pip"]),
        "predicate": "lodges_at",
        "object": None,
        "object_literal": "the Brasswrights attic",
        "assertion": "occurred",
        "speaker": None,
        "evidence": [spans[-1].label],
    }
    mock_extraction(model_api, extraction_ok({**EMPTY_OUTPUT, "facts": [new_fact]}))
    settings = make_settings(
        supersession_resolution_mode="rules",
        supersession_functional_predicates=("lodges_at",),
    )
    service = build_service(retrieval_pool, settings, queue)

    result = await service.process(
        seeded.playthrough_id, time.monotonic() + DEADLINE_SECONDS
    )
    outcome = await collect_outcome(
        retrieval_pool,
        seeded,
        result.counts.input_tokens,
        result.counts.output_tokens,
    )
    score = score_case(case, outcome)

    assert outcome.is_applied
    assert outcome.retired_keys == {"old"}
    assert (score.retired_hits, score.wrongly_retired) == (1, 0)
    assert score.required_hits == 1
    assert score.input_tokens == 100


async def test_filler_facts_are_seeded_for_outside_context_cases(
    db_connection: AsyncConnection,
) -> None:
    case = _case(case_id="ctx_test", filler_subject="pip", filler_count=7)

    seeded = await seed_case(db_connection, case)

    cursor = await db_connection.execute(
        "SELECT count(*) FROM memory_fact WHERE scope_id = %s",
        (seeded.playthrough_id,),
    )
    row = await cursor.fetchone()
    assert row is not None
    assert row[0] == 2 + 7


@pytest.mark.parametrize("case", load_cases() if CASES_FILE.exists() else [])
async def test_every_shipped_case_seeds_and_records_its_rejected_changes(
    db_connection: AsyncConnection, case: StateChangeCase
) -> None:
    seeded = await seed_case(db_connection, case)

    cursor = await db_connection.execute(
        "SELECT count(*) FROM memory_event "
        "WHERE playthrough_id = %s AND event_kind = 'rejected_mutation'",
        (seeded.playthrough_id,),
    )
    row = await cursor.fetchone()
    assert row is not None
    assert row[0] == sum(len(turn.rejected) for turn in case.turns)
    assert set(seeded.fact_ids) == {fact.key for fact in case.prior_facts}
