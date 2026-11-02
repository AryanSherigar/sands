from uuid import uuid4

from app.repositories import scene_exchange_repo, scene_repo
from strategy_contracts.terms import NonAggressionTerm, TermsCard
from strategy_contracts.treaty import Verdict, WeightBand

from tests.repositories.helpers import make_package, seed_playthrough

PROPOSAL = TermsCard(
    proposer_id="valdren",
    counterpart_id="ashford",
    terms=[
        NonAggressionTerm(faction_a="valdren", faction_b="ashford", duration_turns=6)
    ],
)


async def _seed_scene(db_connection):
    await seed_playthrough(db_connection)
    package = make_package()
    await scene_repo.insert_scene(db_connection, package)
    return package.scene_id


async def test_exchanges_are_listed_in_sequence_order(db_connection) -> None:
    scene_id = await _seed_scene(db_connection)
    await scene_exchange_repo.insert_exchange(
        db_connection, scene_id, 2, "second", "reply two", None
    )
    await scene_exchange_repo.insert_exchange(
        db_connection, scene_id, 1, "first", "reply one", None
    )
    rows = await scene_exchange_repo.list_exchanges(db_connection, scene_id)
    assert [row.sequence for row in rows] == [1, 2]
    assert rows[0].player_text == "first"
    assert rows[0].leader_text == "reply one"


async def test_duplicate_sequence_is_ignored_and_first_write_survives(
    db_connection,
) -> None:
    scene_id = await _seed_scene(db_connection)
    first = await scene_exchange_repo.insert_exchange(
        db_connection, scene_id, 1, "hello", "original", None
    )
    second = await scene_exchange_repo.insert_exchange(
        db_connection, scene_id, 1, "hello", "retry", None
    )
    rows = await scene_exchange_repo.list_exchanges(db_connection, scene_id)
    assert (first, second) == (True, False)
    assert [row.leader_text for row in rows] == ["original"]


async def test_proposal_round_trips_as_a_terms_card(db_connection) -> None:
    scene_id = await _seed_scene(db_connection)
    await scene_exchange_repo.insert_exchange(
        db_connection, scene_id, 1, "a pact?", "perhaps", PROPOSAL
    )
    rows = await scene_exchange_repo.list_exchanges(db_connection, scene_id)
    assert rows[0].proposal == PROPOSAL


async def test_unknown_scene_has_no_exchanges(db_connection) -> None:
    await seed_playthrough(db_connection)
    assert await scene_exchange_repo.list_exchanges(db_connection, uuid4()) == []


async def test_cited_grudge_ids_round_trip_and_default_to_empty(db_connection) -> None:
    scene_id = await _seed_scene(db_connection)
    await scene_exchange_repo.insert_exchange(
        db_connection, scene_id, 1, "hello", "plain", None
    )
    await scene_exchange_repo.insert_exchange(
        db_connection, scene_id, 2, "again", "pointed", None, ["g1", "g3"]
    )
    rows = await scene_exchange_repo.list_exchanges(db_connection, scene_id)
    assert [row.cited_grudge_ids for row in rows] == [[], ["g1", "g3"]]


async def test_verdict_round_trips_and_defaults_to_none(db_connection) -> None:
    scene_id = await _seed_scene(db_connection)
    await scene_exchange_repo.insert_exchange(
        db_connection, scene_id, 1, "a", "b", None, verdict=Verdict.HAGGLE
    )
    await scene_exchange_repo.insert_exchange(
        db_connection, scene_id, 2, "c", "d", None
    )

    rows = await scene_exchange_repo.list_exchanges(db_connection, scene_id)

    assert [row.verdict for row in rows] == [Verdict.HAGGLE, None]


async def test_clause_bands_round_trip_in_order_and_default_to_empty(
    db_connection,
) -> None:
    scene_id = await _seed_scene(db_connection)
    bands = [WeightBand.HEAVY, WeightBand.LIGHT]
    await scene_exchange_repo.insert_exchange(
        db_connection, scene_id, 1, "a", "b", PROPOSAL, clause_bands=bands
    )
    await scene_exchange_repo.insert_exchange(
        db_connection, scene_id, 2, "c", "d", None
    )

    rows = await scene_exchange_repo.list_exchanges(db_connection, scene_id)

    assert [row.clause_bands for row in rows] == [bands, []]
