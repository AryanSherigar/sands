import type {
  CreatorStatsOverviewResponse,
  ScenarioStatsResponse,
} from "../types/stats.types";

export const buildOverview = (
  overrides: Partial<CreatorStatsOverviewResponse> = {},
): CreatorStatsOverviewResponse => ({
  stats_range: "30d",
  bucket: "day",
  has_published_scenarios: true,
  is_sample_sufficient: true,
  sample_threshold: 5,
  totals: {
    plays: { value: 12, trend: { percent_change: 0.2, is_new: false } },
    players: { value: 9, trend: null },
    average_rating: { value: 4.5, trend: null },
    completion_rate: { value: 0.5, trend: null },
  },
  series: [
    { bucket_start: "2026-10-27", plays: 5 },
    { bucket_start: "2026-10-27", plays: 7 },
  ],
  scenarios: [
    {
      scenario_id: "scn-1",
      title: "The Hollow Cairn",
      status: "published",
      plays: 12,
      trend: { percent_change: 0.2, is_new: false },
      completion_rate: 0.5,
      average_turns: 8.5,
      average_rating: 4.5,
    },
  ],
  highlights: {
    most_played: { scenario_id: "scn-1", title: "The Hollow Cairn", value: 12 },
    biggest_drop_off: null,
    latest_reviews: [],
  },
  ...overrides,
});

export const buildScenarioStats = (
  overrides: Partial<ScenarioStatsResponse> = {},
): ScenarioStatsResponse => ({
  scenario: {
    scenario_id: "scn-1",
    title: "The Hollow Cairn",
    status: "published",
    mode: "master",
    genre_tags: ["fantasy"],
    has_stats: true,
  },
  stats_range: "30d",
  bucket: "day",
  is_sample_sufficient: true,
  sample_threshold: 5,
  plays: {
    total_plays: 10,
    active_count: 2,
    ended_count: 6,
    abandoned_count: 2,
    distinct_players: 8,
    repeat_players: 2,
    multiplayer_rate: 0.3,
    series: [
      { bucket_start: "2026-10-27", plays: 4 },
      { bucket_start: "2026-10-27", plays: 6 },
    ],
  },
  engagement: {
    average_turns: 8,
    median_turns: 7,
    turn_distribution: [
      { label: "0", count: 0 },
      { label: "1-2", count: 2 },
      { label: "3-4", count: 8 },
    ],
  },
  funnel: {
    steps: [
      { label: "Started", count: 10, rate: 1 },
      { label: "Reached turn 3", count: 8, rate: 0.8 },
      { label: "Reached turn 10", count: 6, rate: 0.6 },
      { label: "Ended", count: 6, rate: 0.6 },
    ],
    retention_rate: 0.25,
  },
  outcomes: {
    win_count: 4,
    lose_count: 2,
    win_rate: 4 / 6,
    lose_rate: 2 / 6,
    end_conditions: [
      { title: "Escaped the cairn", count: 4, rate: 4 / 6 },
      { title: "Devoured", count: 2, rate: 2 / 6 },
    ],
  },
  reviews: {
    review_count: 3,
    average_rating: 4.7,
    histogram: [
      { rating: 1, count: 0 },
      { rating: 2, count: 0 },
      { rating: 3, count: 0 },
      { rating: 4, count: 1 },
      { rating: 5, count: 2 },
    ],
    latest: [
      {
        scenario_id: "scn-1",
        scenario_title: "The Hollow Cairn",
        author_display_name: "Eldrin",
        rating: 5,
        comment: "Loved the cairn.",
        created_at: "2026-10-27T10:00:00Z",
      },
    ],
    bookmark_count: 4,
    share_counts: { spectate: 2, join: 1 },
  },
  versions: [
    { scenario_version: 2, plays: 7, completion_rate: 0.57, win_rate: 0.5, average_turns: 8.1 },
    { scenario_version: 1, plays: 3, completion_rate: null, win_rate: null, average_turns: null },
  ],
  benchmarks: {
    peer_count: 6,
    peer_scope: "genre",
    metrics: [
      { key: "completion_rate", value: 0.6, peer_median: 0.48 },
      { key: "average_turns", value: 8, peer_median: 7 },
      { key: "average_rating", value: 4.7, peer_median: 4.1 },
      { key: "win_rate", value: 0.67, peer_median: 0.4 },
    ],
  },
  heatmap: [
    {
      map_id: "map-1",
      name: "The Cairn",
      image_url: null,
      pins: [
        { entity_id: "loc-1", name: "Entrance", x: 0.1, y: 0.2, discovery_rate: 1 },
        { entity_id: "loc-2", name: "Inner chamber", x: 0.7, y: 0.8, discovery_rate: 0.3 },
      ],
    },
  ],
  ...overrides,
});
