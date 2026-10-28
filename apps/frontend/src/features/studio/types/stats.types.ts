import type { ScenarioMode, ScenarioStatus } from "./scenario.types";

export type StatsRange = "7d" | "30d" | "90d" | "all";
export type StatsBucket = "day" | "week";
export type BenchmarkKey = "completion_rate" | "average_turns" | "average_rating" | "win_rate";
export type PeerScope = "genre" | "mode";

interface EndConditionHit {
  title: string;
  count: number;
  rate: number | null;
}

export interface VersionRow {
  scenario_version: number;
  plays: number;
  completion_rate: number | null;
  win_rate: number | null;
  average_turns: number | null;
}

interface BenchmarkMetric {
  key: BenchmarkKey;
  value: number | null;
  peer_median: number | null;
}

export interface BenchmarkSection {
  peer_count: number;
  peer_scope: PeerScope;
  metrics: BenchmarkMetric[];
}

interface HeatmapPin {
  entity_id: string;
  name: string;
  x: number;
  y: number;
  discovery_rate: number | null;
}

export interface HeatmapMap {
  map_id: string;
  name: string;
  image_url: string | null;
  pins: HeatmapPin[];
}

export interface Trend {
  percent_change: number | null;
  is_new: boolean;
}

export interface SeriesPoint {
  bucket_start: string;
  plays: number;
}

interface TurnBucket {
  label: string;
  count: number;
}

interface RatingBucket {
  rating: number;
  count: number;
}

interface FunnelStep {
  label: string;
  count: number;
  rate: number | null;
}

export interface ReviewItem {
  scenario_id: string;
  scenario_title: string;
  author_display_name: string;
  rating: number;
  comment: string | null;
  created_at: string;
}

interface ShareCounts {
  spectate: number;
  join: number;
}

export interface StatsScenarioSummary {
  scenario_id: string;
  title: string;
  status: ScenarioStatus;
  mode: ScenarioMode;
  genre_tags: string[];
  has_stats: boolean;
}

interface PlaysSection {
  total_plays: number;
  active_count: number;
  ended_count: number;
  abandoned_count: number;
  distinct_players: number;
  repeat_players: number;
  multiplayer_rate: number | null;
  series: SeriesPoint[];
}

export interface EngagementSection {
  average_turns: number | null;
  median_turns: number | null;
  turn_distribution: TurnBucket[];
}

export interface FunnelSection {
  steps: FunnelStep[];
  retention_rate: number | null;
}

export interface OutcomesSection {
  win_count: number;
  lose_count: number;
  win_rate: number | null;
  lose_rate: number | null;
  end_conditions: EndConditionHit[];
}

export interface ReviewsSection {
  review_count: number;
  average_rating: number | null;
  histogram: RatingBucket[];
  latest: ReviewItem[];
  bookmark_count: number;
  share_counts: ShareCounts;
}

export interface ScenarioStatsResponse {
  scenario: StatsScenarioSummary;
  stats_range: StatsRange;
  bucket: StatsBucket;
  is_sample_sufficient: boolean;
  sample_threshold: number;
  plays: PlaysSection;
  engagement: EngagementSection;
  funnel: FunnelSection;
  outcomes: OutcomesSection | null;
  reviews: ReviewsSection;
  versions: VersionRow[];
  benchmarks: BenchmarkSection | null;
  heatmap: HeatmapMap[];
}

interface HeadlineMetric {
  value: number | null;
  trend: Trend | null;
}

export interface OverviewTotals {
  plays: HeadlineMetric;
  players: HeadlineMetric;
  average_rating: HeadlineMetric;
  completion_rate: HeadlineMetric;
}

export interface OverviewScenarioRow {
  scenario_id: string;
  title: string;
  status: ScenarioStatus;
  plays: number;
  trend: Trend | null;
  completion_rate: number | null;
  average_turns: number | null;
  average_rating: number | null;
}

export interface OverviewHighlight {
  scenario_id: string;
  title: string;
  value: number;
}

export interface OverviewHighlights {
  most_played: OverviewHighlight | null;
  biggest_drop_off: OverviewHighlight | null;
  latest_reviews: ReviewItem[];
}

export interface CreatorStatsOverviewResponse {
  stats_range: StatsRange;
  bucket: StatsBucket;
  has_published_scenarios: boolean;
  is_sample_sufficient: boolean;
  sample_threshold: number;
  totals: OverviewTotals;
  series: SeriesPoint[];
  scenarios: OverviewScenarioRow[];
  highlights: OverviewHighlights;
}
