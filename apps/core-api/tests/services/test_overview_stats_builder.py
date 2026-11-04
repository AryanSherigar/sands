import uuid
from datetime import UTC, datetime

from app.db.models.scenario import Scenario
from app.repositories.creator_stats_repo import PlaythroughTotalsRow
from app.services.overview_stats_builder import (
    OverviewData,
    OverviewPeriod,
    build_overview,
)
from app.services.stats_window import build_stats_window

NOW = datetime(2026, 10, 26, 12, 0, tzinfo=UTC)
WINDOW = build_stats_window("30d", NOW)
ALL_TIME_WINDOW = build_stats_window("all", NOW)


def make_scenario(title: str) -> Scenario:
    return Scenario(
        scenario_id=uuid.uuid4(),
        creator_id=uuid.uuid4(),
        title=title,
        mode="master",
        status="published",
        genre_tags=[],
        complexity_tier="master",
        player_count_support="solo",
    )


def make_totals(
    scenario: Scenario, plays: int, ended: int = 0, reached: tuple[int, int] = (0, 0)
) -> PlaythroughTotalsRow:
    return PlaythroughTotalsRow(
        scenario_id=scenario.scenario_id,
        plays=plays,
        active_count=plays - ended,
        ended_count=ended,
        abandoned_count=0,
        win_count=0,
        lose_count=0,
        turn_total=plays * 4,
        multiplayer_count=0,
        distinct_players=plays,
        reached_turn_counts=reached,
    )


def period(
    totals: list[PlaythroughTotalsRow],
    players: int,
    ratings: list[tuple[uuid.UUID, int, int]] | None = None,
) -> OverviewPeriod:
    return OverviewPeriod(
        totals=totals, distinct_players=players, rating_rows=ratings or []
    )


def test_overview_for_scenarios_with_no_plays() -> None:
    scenario = make_scenario("Quiet")
    data = OverviewData(
        scenarios=[scenario],
        current=period([], 0),
        previous=period([], 0),
        series=[],
        latest_reviews=[],
    )
    response = build_overview(data, "30d", WINDOW)
    assert response.has_published_scenarios is True
    assert response.is_sample_sufficient is False
    assert response.totals.plays.value == 0
    assert response.totals.completion_rate.value is None
    assert response.scenarios[0].plays == 0
    assert response.scenarios[0].completion_rate is None
    assert response.highlights.most_played is None
    assert all(point.plays == 0 for point in response.series)


def test_totals_trends_and_ratings() -> None:
    first, second = make_scenario("First"), make_scenario("Second")
    current = period(
        [
            make_totals(first, 6, ended=3, reached=(5, 3)),
            make_totals(second, 6, ended=3, reached=(6, 2)),
        ],
        players=9,
        ratings=[(first.scenario_id, 5, 1), (second.scenario_id, 3, 1)],
    )
    previous = period([make_totals(first, 10, ended=2)], players=9)
    data = OverviewData([first, second], current, previous, [], [])

    totals = build_overview(data, "30d", WINDOW).totals

    assert totals.plays.value == 12
    assert totals.plays.trend is not None
    assert totals.plays.trend.percent_change == 0.2
    assert totals.players.trend is not None
    assert totals.players.trend.percent_change == 0.0
    assert totals.average_rating.value == 4.0
    assert totals.average_rating.trend is None
    assert totals.completion_rate.value == 0.5


def test_rows_sorted_by_plays_with_row_trends() -> None:
    small, big = make_scenario("Small"), make_scenario("Big")
    current = period([make_totals(small, 2), make_totals(big, 7, ended=7)], players=9)
    previous = period([make_totals(big, 7)], players=7)
    rows = build_overview(
        OverviewData([small, big], current, previous, [], []), "30d", WINDOW
    ).scenarios

    assert [row.title for row in rows] == ["Big", "Small"]
    assert rows[0].completion_rate == 1.0
    assert rows[1].completion_rate is None
    assert rows[1].trend is not None
    assert rows[1].trend.is_new is True


def test_all_time_has_no_trends() -> None:
    scenario = make_scenario("Solo")
    current = period([make_totals(scenario, 6)], players=6)
    response = build_overview(
        OverviewData([scenario], current, None, [], []), "all", ALL_TIME_WINDOW
    )
    assert response.totals.plays.trend is None
    assert response.scenarios[0].trend is None


def test_highlights_pick_most_played_and_biggest_drop() -> None:
    steady, leaky, tiny = (
        make_scenario("Steady"),
        make_scenario("Leaky"),
        make_scenario("Tiny"),
    )
    current = period(
        [
            make_totals(steady, 20, reached=(18, 16)),
            make_totals(leaky, 8, reached=(8, 2)),
            make_totals(tiny, 3, reached=(3, 0)),
        ],
        players=30,
    )
    highlights = build_overview(
        OverviewData([steady, leaky, tiny], current, None, [], []),
        "all",
        ALL_TIME_WINDOW,
    ).highlights

    assert highlights.most_played is not None
    assert highlights.most_played.title == "Steady"
    assert highlights.most_played.value == 20
    assert highlights.biggest_drop_off is not None
    assert highlights.biggest_drop_off.title == "Leaky"
    assert highlights.biggest_drop_off.value == 0.75


def test_no_scenarios_flags_empty_state() -> None:
    data = OverviewData([], period([], 0), period([], 0), [], [])
    assert build_overview(data, "30d", WINDOW).has_published_scenarios is False
