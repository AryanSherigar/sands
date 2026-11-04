import uuid
from datetime import UTC, datetime

from app.db.models.scenario import Scenario
from app.repositories.creator_stats_repo import (
    LatestReviewRow,
    MapPinRow,
    PeerMediansRow,
    PlaythroughTotalsRow,
    VersionTotalsRow,
)
from app.services.scenario_stats_builder import (
    PeerMatch,
    ScenarioStatsData,
    build_scenario_stats,
    peer_scopes,
)
from app.services.stats_window import build_stats_window

NOW = datetime(2026, 10, 26, 12, 0, tzinfo=UTC)
WINDOW = build_stats_window("7d", NOW)
SCENARIO_ID = uuid.uuid4()


def make_scenario(mode: str = "master", status: str = "published") -> Scenario:
    return Scenario(
        scenario_id=SCENARIO_ID,
        creator_id=uuid.uuid4(),
        title="The Hollow Cairn",
        mode=mode,
        status=status,
        genre_tags=["fantasy"],
        complexity_tier=mode,
        player_count_support="solo",
    )


def make_totals(plays: int = 10, distinct_players: int = 8) -> PlaythroughTotalsRow:
    return PlaythroughTotalsRow(
        scenario_id=SCENARIO_ID,
        plays=plays,
        active_count=2,
        ended_count=6,
        abandoned_count=2,
        win_count=4,
        lose_count=2,
        turn_total=80,
        multiplayer_count=3,
        distinct_players=distinct_players,
        reached_turn_counts=(8, 6),
    )


def test_scenario_stats_with_no_playthroughs_returns_zeros() -> None:
    response = build_scenario_stats(make_scenario(), "7d", WINDOW, ScenarioStatsData())
    assert response.plays.total_plays == 0
    assert response.is_sample_sufficient is False
    assert response.sample_threshold == 5
    assert response.plays.multiplayer_rate is None
    assert response.engagement.average_turns is None
    assert [step.count for step in response.funnel.steps] == [0, 0, 0, 0]
    assert len(response.plays.series) == 8
    assert all(point.plays == 0 for point in response.plays.series)


def test_sufficient_sample_builds_funnel_rates_and_retention() -> None:
    data = ScenarioStatsData(totals=make_totals(), repeat_players=2)
    response = build_scenario_stats(make_scenario(), "7d", WINDOW, data)
    assert response.is_sample_sufficient is True
    assert [step.label for step in response.funnel.steps] == [
        "Started",
        "Reached turn 3",
        "Reached turn 10",
        "Ended",
    ]
    assert [step.count for step in response.funnel.steps] == [10, 8, 6, 6]
    assert [step.rate for step in response.funnel.steps] == [1.0, 0.8, 0.6, 0.6]
    assert response.funnel.retention_rate == 0.25
    assert response.plays.multiplayer_rate == 0.3


def test_under_threshold_hides_rates_but_keeps_counts() -> None:
    data = ScenarioStatsData(
        totals=make_totals(plays=4, distinct_players=3), repeat_players=1
    )
    response = build_scenario_stats(make_scenario(), "7d", WINDOW, data)
    assert response.is_sample_sufficient is False
    assert response.plays.total_plays == 4
    assert response.outcomes is not None
    assert response.outcomes.win_count == 4
    assert response.outcomes.win_rate is None
    assert response.funnel.retention_rate is None


def test_master_outcome_rates_use_ended_denominator() -> None:
    response = build_scenario_stats(
        make_scenario(), "7d", WINDOW, ScenarioStatsData(totals=make_totals())
    )
    assert response.outcomes is not None
    assert response.outcomes.win_rate == 4 / 6
    assert response.outcomes.lose_rate == 2 / 6


def test_newbie_scenario_has_no_outcomes() -> None:
    response = build_scenario_stats(
        make_scenario(mode="newbie"),
        "7d",
        WINDOW,
        ScenarioStatsData(totals=make_totals()),
    )
    assert response.outcomes is None


def test_draft_scenario_has_no_stats_flag() -> None:
    response = build_scenario_stats(
        make_scenario(status="draft"), "7d", WINDOW, ScenarioStatsData()
    )
    assert response.scenario.has_stats is False


def test_reviews_section_histogram_and_shares() -> None:
    review = LatestReviewRow(
        scenario_id=SCENARIO_ID,
        scenario_title="The Hollow Cairn",
        author_display_name="Eldrin",
        rating=5,
        comment="Great",
        created_at=NOW,
    )
    data = ScenarioStatsData(
        rating_counts={5: 2, 4: 1},
        latest_reviews=[review],
        bookmark_count=3,
        share_counts={"spectate": 2},
    )
    reviews = build_scenario_stats(make_scenario(), "7d", WINDOW, data).reviews
    assert reviews.review_count == 3
    assert reviews.average_rating == 14 / 3
    assert [bucket.count for bucket in reviews.histogram] == [0, 0, 0, 1, 2]
    assert reviews.latest[0].author_display_name == "Eldrin"
    assert (reviews.share_counts.spectate, reviews.share_counts.join) == (2, 0)
    assert reviews.bookmark_count == 3


MEDIANS = PeerMediansRow(
    peer_count=6,
    completion_rate=0.5,
    average_turns=7.0,
    win_rate=0.4,
    average_rating=4.1,
    win_rate_peer_count=6,
    rating_peer_count=6,
)


def test_end_condition_rates_use_ended_denominator() -> None:
    data = ScenarioStatsData(
        totals=make_totals(),
        end_condition_counts=[("Escaped", 3), ("Devoured", 3)],
    )
    outcomes = build_scenario_stats(make_scenario(), "7d", WINDOW, data).outcomes
    assert outcomes is not None
    assert [(hit.title, hit.count, hit.rate) for hit in outcomes.end_conditions] == [
        ("Escaped", 3, 0.5),
        ("Devoured", 3, 0.5),
    ]


def test_versions_gate_each_row_and_skip_win_rate_for_newbie() -> None:
    versions = [
        VersionTotalsRow(
            scenario_version=2, plays=6, ended_count=3, win_count=2, turn_total=30
        ),
        VersionTotalsRow(
            scenario_version=1, plays=2, ended_count=2, win_count=1, turn_total=10
        ),
    ]
    master = build_scenario_stats(
        make_scenario(), "7d", WINDOW, ScenarioStatsData(version_totals=versions)
    )
    newbie = build_scenario_stats(
        make_scenario(mode="newbie"),
        "7d",
        WINDOW,
        ScenarioStatsData(version_totals=versions),
    )

    assert master.versions[0].completion_rate == 0.5
    assert master.versions[0].win_rate == 2 / 3
    assert master.versions[0].average_turns == 5.0
    assert master.versions[1].completion_rate is None
    assert newbie.versions[0].win_rate is None


def test_benchmarks_compare_scenario_to_peer_medians() -> None:
    data = ScenarioStatsData(
        totals=make_totals(),
        rating_counts={5: 1, 3: 1},
        peer_match=PeerMatch(scope="genre", medians=MEDIANS),
    )
    benchmarks = build_scenario_stats(make_scenario(), "7d", WINDOW, data).benchmarks
    assert benchmarks is not None
    assert (benchmarks.peer_count, benchmarks.peer_scope) == (6, "genre")
    by_key = {metric.key: metric for metric in benchmarks.metrics}
    assert by_key["completion_rate"].value == 0.6
    assert by_key["completion_rate"].peer_median == 0.5
    assert by_key["average_turns"].value == 8.0
    assert by_key["average_rating"].value == 4.0
    assert by_key["win_rate"].value == 4 / 6


def test_benchmarks_hidden_without_peers_or_sample() -> None:
    no_peers = build_scenario_stats(
        make_scenario(), "7d", WINDOW, ScenarioStatsData(totals=make_totals())
    )
    thin = build_scenario_stats(
        make_scenario(),
        "7d",
        WINDOW,
        ScenarioStatsData(
            totals=make_totals(plays=3),
            peer_match=PeerMatch(scope="mode", medians=MEDIANS),
        ),
    )
    assert no_peers.benchmarks is None
    assert thin.benchmarks is None


def test_newbie_benchmarks_have_no_win_rate() -> None:
    data = ScenarioStatsData(
        totals=make_totals(), peer_match=PeerMatch(scope="mode", medians=MEDIANS)
    )
    benchmarks = build_scenario_stats(
        make_scenario(mode="newbie"), "7d", WINDOW, data
    ).benchmarks
    assert benchmarks is not None
    assert "win_rate" not in {metric.key for metric in benchmarks.metrics}


def test_heatmap_groups_pins_by_map_with_discovery_rates() -> None:
    map_id, entity_a, entity_b = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    pins = [
        MapPinRow(map_id, "Cairn", None, entity_a, "Entrance", 0.1, 0.2),
        MapPinRow(map_id, "Cairn", None, entity_b, "Chamber", 0.7, 0.8),
    ]
    data = ScenarioStatsData(
        totals=make_totals(), map_pins=pins, discovery_counts={str(entity_a): 5}
    )
    heatmap = build_scenario_stats(make_scenario(), "7d", WINDOW, data).heatmap
    assert len(heatmap) == 1
    assert [(pin.name, pin.discovery_rate) for pin in heatmap[0].pins] == [
        ("Entrance", 0.5),
        ("Chamber", 0.0),
    ]


def test_peer_scopes_try_genre_first_only_when_tagged() -> None:
    tagged = make_scenario()
    untagged = make_scenario()
    untagged.genre_tags = []
    assert peer_scopes(tagged) == [("genre", ["fantasy"]), ("mode", None)]
    assert peer_scopes(untagged) == [("mode", None)]


def test_benchmark_hides_medians_backed_by_too_few_peers() -> None:
    thin_medians = PeerMediansRow(
        peer_count=6,
        completion_rate=0.5,
        average_turns=7.0,
        win_rate=0.4,
        average_rating=4.0,
        win_rate_peer_count=6,
        rating_peer_count=1,
    )
    data = ScenarioStatsData(
        totals=make_totals(), peer_match=PeerMatch(scope="genre", medians=thin_medians)
    )
    benchmarks = build_scenario_stats(make_scenario(), "7d", WINDOW, data).benchmarks
    assert benchmarks is not None
    by_key = {metric.key: metric for metric in benchmarks.metrics}
    assert by_key["average_rating"].peer_median is None
    assert by_key["win_rate"].peer_median == 0.4
