"""Integration tests for EndingsRepo."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.repositories.endings_repo import EndingsRepo
from sqlalchemy.ext.asyncio import AsyncSession
from tests.stats_factories import add_playthrough, make_scenario, make_user

BASE = datetime(2026, 10, 26, tzinfo=UTC)


def condition(title: str, tag: str = "win", is_secret: bool = False) -> dict:
    return {
        "outcome_title": title,
        "outcome_tag": tag,
        "is_secret": is_secret,
        "priority": 0,
    }


@pytest.mark.asyncio
async def test_ended_runs_only_mine_finished_and_non_playtest(
    db_session: AsyncSession,
) -> None:
    me = await make_user(db_session, "Me")
    other = await make_user(db_session, "Other")
    scenario = await make_scenario(db_session, me)
    ending_id = uuid.uuid4()
    await add_playthrough(
        db_session,
        scenario,
        me,
        turn_count=5,
        status="completed",
        outcome_tag="win",
        outcome_title="Ashen",
        outcome_id=ending_id,
    )
    await add_playthrough(
        db_session,
        scenario,
        me,
        turn_count=5,
        status="completed",
        outcome_tag="lose",
        outcome_title="Consumed",
    )
    await add_playthrough(db_session, scenario, me, turn_count=5)  # active
    await add_playthrough(
        db_session,
        scenario,
        me,
        turn_count=5,
        status="completed",
        outcome_tag="win",
        outcome_title="Test",
        is_playtest=True,
    )
    await add_playthrough(
        db_session,
        scenario,
        other,
        turn_count=5,
        status="completed",
        outcome_tag="win",
        outcome_title="Theirs",
    )

    rows = await EndingsRepo(db_session).list_ended_runs(me.user_id)

    assert sorted(
        (r.outcome_title, r.outcome_tag, r.outcome_id is not None) for r in rows
    ) == [("Ashen", "win", True), ("Consumed", "lose", False)]
    assert {r.scenario_id for r in rows} == {scenario.scenario_id}


@pytest.mark.asyncio
async def test_latest_snapshot_is_the_most_recent_played_run_per_scenario(
    db_session: AsyncSession,
) -> None:
    me = await make_user(db_session)
    scen_a = await make_scenario(db_session, me)
    scen_b = await make_scenario(db_session, me)
    await add_playthrough(
        db_session,
        scen_a,
        me,
        turn_count=3,
        created_at=BASE,
        snapshot={"end_conditions": [condition("Old")]},
    )
    await add_playthrough(
        db_session,
        scen_a,
        me,
        turn_count=4,
        created_at=BASE + timedelta(days=2),
        snapshot={"end_conditions": [condition("New", "lose")]},
    )
    await add_playthrough(
        db_session,
        scen_a,
        me,
        turn_count=0,
        created_at=BASE + timedelta(days=5),
        snapshot={"end_conditions": [condition("NoTurns")]},
    )
    await add_playthrough(
        db_session,
        scen_a,
        me,
        turn_count=9,
        created_at=BASE + timedelta(days=9),
        is_playtest=True,
        snapshot={"end_conditions": [condition("Playtest")]},
    )
    await add_playthrough(
        db_session,
        scen_b,
        me,
        turn_count=2,
        created_at=BASE + timedelta(days=3),
        snapshot={},
    )

    rows = await EndingsRepo(db_session).list_latest_snapshot_endings(me.user_id)

    by_scenario = {row.scenario_id: row for row in rows}
    assert [
        c["outcome_title"] for c in by_scenario[scen_a.scenario_id].end_conditions
    ] == ["New"]
    assert by_scenario[scen_b.scenario_id].end_conditions == []
    assert rows[0].scenario_id == scen_b.scenario_id  # most recently played first


@pytest.mark.asyncio
async def test_latest_snapshot_excludes_other_users_and_unplayed(
    db_session: AsyncSession,
) -> None:
    me = await make_user(db_session, "Me")
    other = await make_user(db_session, "Other")
    scenario = await make_scenario(db_session, other)
    await add_playthrough(
        db_session,
        scenario,
        other,
        turn_count=5,
        snapshot={"end_conditions": [condition("Theirs")]},
    )
    await add_playthrough(
        db_session,
        scenario,
        me,
        turn_count=0,
        snapshot={"end_conditions": [condition("Unplayed")]},
    )

    rows = await EndingsRepo(db_session).list_latest_snapshot_endings(me.user_id)

    assert rows == []
