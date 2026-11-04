"""Slice 2 aggregations: versions, end conditions, peers, map discovery."""

import uuid

import pytest
from app.db.models.entity import Entity
from app.db.models.map_pin import MapPin
from app.db.models.review import ScenarioReview
from app.db.models.scenario import Scenario
from app.db.models.scenario_map import ScenarioMap
from app.db.models.user import User
from app.repositories.creator_stats_repo import CreatorStatsRepo, PeerFilter
from sqlalchemy.ext.asyncio import AsyncSession
from tests.stats_factories import (
    RECENT,
    STATS_NOW,
    WINDOW_START,
    add_playthrough,
    make_scenario,
    make_user,
)


async def add_peer(
    session: AsyncSession,
    creator: User,
    player: User,
    genre_tag: str,
    ended: int,
    plays: int = 5,
    mode: str = "master",
) -> Scenario:
    scenario = await make_scenario(session, creator, mode=mode, genre_tags=[genre_tag])
    for index in range(plays):
        is_ended = index < ended
        await add_playthrough(
            session,
            scenario,
            player,
            turn_count=4,
            status="completed" if is_ended else "active",
            outcome_tag="win" if is_ended else None,
        )
    return scenario


@pytest.mark.asyncio
async def test_version_totals_group_by_version(db_session: AsyncSession) -> None:
    creator = await make_user(db_session, "Creator")
    alice = await make_user(db_session, "Alice")
    scenario = await make_scenario(db_session, creator)
    await add_playthrough(db_session, scenario, alice, turn_count=5, scenario_version=1)
    await add_playthrough(
        db_session,
        scenario,
        alice,
        turn_count=9,
        status="completed",
        outcome_tag="win",
        scenario_version=2,
    )
    await add_playthrough(db_session, scenario, alice, turn_count=3, scenario_version=2)

    rows = await CreatorStatsRepo(db_session).get_version_totals(
        scenario.scenario_id, WINDOW_START, STATS_NOW
    )

    assert [
        (
            row.scenario_version,
            row.plays,
            row.ended_count,
            row.win_count,
            row.turn_total,
        )
        for row in rows
    ] == [(2, 2, 1, 1, 12), (1, 1, 0, 0, 5)]


@pytest.mark.asyncio
async def test_end_condition_counts_most_common_first(db_session: AsyncSession) -> None:
    creator = await make_user(db_session, "Creator")
    alice = await make_user(db_session, "Alice")
    scenario = await make_scenario(db_session, creator)
    for title, tag in (("Escaped", "win"), ("Escaped", "win"), ("Devoured", "lose")):
        await add_playthrough(
            db_session,
            scenario,
            alice,
            status="completed",
            outcome_tag=tag,
            outcome_title=title,
        )
    await add_playthrough(db_session, scenario, alice)

    counts = await CreatorStatsRepo(db_session).get_end_condition_counts(
        scenario.scenario_id, WINDOW_START, STATS_NOW
    )

    assert counts == [("Escaped", 2), ("Devoured", 1)]


@pytest.mark.asyncio
async def test_peer_medians_by_shared_genre(db_session: AsyncSession) -> None:
    creator = await make_user(db_session, "Creator")
    player = await make_user(db_session, "Player")
    tag = f"genre-{uuid.uuid4().hex[:8]}"
    target = await add_peer(db_session, creator, player, tag, ended=0)
    peers = [
        await add_peer(db_session, creator, player, tag, ended=ended)
        for ended in (1, 2, 3, 4, 5)
    ]
    await add_peer(db_session, creator, player, tag, ended=4, plays=4)
    await add_peer(db_session, creator, player, tag, ended=5, mode="newbie")
    for peer, rating in ((peers[0], 3), (peers[1], 5)):
        reviewer = await make_user(db_session, "Reviewer")
        db_session.add(
            ScenarioReview(
                scenario_id=peer.scenario_id,
                user_id=reviewer.user_id,
                rating=rating,
                created_at=RECENT,
            )
        )
    await db_session.flush()

    medians = await CreatorStatsRepo(db_session).get_peer_medians(
        PeerFilter(
            exclude_scenario_id=target.scenario_id, mode="master", genre_tags=[tag]
        ),
        WINDOW_START,
        STATS_NOW,
        5,
    )

    assert medians.peer_count == 5
    assert medians.completion_rate == pytest.approx(0.6)
    assert medians.average_turns == pytest.approx(4.0)
    assert medians.win_rate == pytest.approx(1.0)
    assert medians.average_rating == pytest.approx(4.0)
    assert medians.win_rate_peer_count == 5
    assert medians.rating_peer_count == 2


@pytest.mark.asyncio
async def test_peer_medians_mode_scope_ignores_genre(db_session: AsyncSession) -> None:
    creator = await make_user(db_session, "Creator")
    player = await make_user(db_session, "Player")
    target = await add_peer(
        db_session, creator, player, f"genre-{uuid.uuid4().hex[:8]}", ended=0
    )
    for _ in range(5):
        await add_peer(
            db_session, creator, player, f"genre-{uuid.uuid4().hex[:8]}", ended=5
        )

    medians = await CreatorStatsRepo(db_session).get_peer_medians(
        PeerFilter(
            exclude_scenario_id=target.scenario_id, mode="master", genre_tags=None
        ),
        WINDOW_START,
        STATS_NOW,
        5,
    )

    assert medians.peer_count >= 5


async def add_location_pin(
    session: AsyncSession,
    scenario: Scenario,
    scenario_map: ScenarioMap,
    name: str,
    x: float,
    y: float,
) -> Entity:
    entity = Entity(
        scenario_id=scenario.scenario_id, entity_type="location", canonical_name=name
    )
    session.add(entity)
    await session.flush()
    session.add(
        MapPin(
            map_id=scenario_map.map_id,
            scenario_id=scenario.scenario_id,
            entity_id=entity.entity_id,
            x=x,
            y=y,
        )
    )
    await session.flush()
    return entity


@pytest.mark.asyncio
async def test_map_pins_and_discovery_counts(db_session: AsyncSession) -> None:
    creator = await make_user(db_session, "Creator")
    alice = await make_user(db_session, "Alice")
    scenario = await make_scenario(db_session, creator)
    scenario_map = ScenarioMap(
        scenario_id=scenario.scenario_id,
        name="Cairn",
        image_url="https://example.test/cairn.png",
    )
    db_session.add(scenario_map)
    await db_session.flush()
    entrance = await add_location_pin(
        db_session, scenario, scenario_map, "Entrance", 0.1, 0.2
    )
    chamber = await add_location_pin(
        db_session, scenario, scenario_map, "Chamber", 0.7, 0.8
    )
    await add_playthrough(
        db_session,
        scenario,
        alice,
        state={
            "discovered_location_ids": [str(entrance.entity_id), str(chamber.entity_id)]
        },
    )
    await add_playthrough(
        db_session,
        scenario,
        alice,
        state={"discovered_location_ids": [str(entrance.entity_id)]},
    )
    await add_playthrough(
        db_session,
        scenario,
        creator,
        is_playtest=True,
        state={"discovered_location_ids": [str(chamber.entity_id)]},
    )
    repo = CreatorStatsRepo(db_session)

    pins = await repo.list_map_pins(scenario.scenario_id)
    counts = await repo.get_discovery_counts(
        scenario.scenario_id, WINDOW_START, STATS_NOW
    )

    assert [(pin.entity_name, pin.x, pin.y, pin.map_name) for pin in pins] == [
        ("Chamber", 0.7, 0.8, "Cairn"),
        ("Entrance", 0.1, 0.2, "Cairn"),
    ]
    assert counts == {str(entrance.entity_id): 2, str(chamber.entity_id): 1}


@pytest.mark.asyncio
async def test_discovery_counts_ignore_non_array_state(
    db_session: AsyncSession,
) -> None:
    creator = await make_user(db_session, "Creator")
    alice = await make_user(db_session, "Alice")
    scenario = await make_scenario(db_session, creator)
    await add_playthrough(
        db_session, scenario, alice, state={"discovered_location_ids": "not-a-list"}
    )
    await add_playthrough(db_session, scenario, alice, state={})
    await add_playthrough(
        db_session, scenario, alice, state={"discovered_location_ids": None}
    )

    counts = await CreatorStatsRepo(db_session).get_discovery_counts(
        scenario.scenario_id, WINDOW_START, STATS_NOW
    )

    assert counts == {}
