import type { ScenarioStatus } from "../types/scenario.types";
import type { BenchmarkKey, PeerScope, StatsRange } from "../types/stats.types";
import type {
  ChartTone,
  ScenarioTableColumn,
  StatsSectionLink,
} from "../types/statsView.types";

export const STATS_RANGES: readonly StatsRange[] = ["7d", "30d", "90d", "all"];
export const DEFAULT_STATS_RANGE: StatsRange = "30d";
export const STATS_RANGE_PARAM = "range";
export const STATS_STALE_TIME_MS = 60_000;
export const STATS_VISIBLE_STATUSES: readonly ScenarioStatus[] = [
  "published",
  "archived",
];

export const STATS_RANGE_LABELS: Record<StatsRange, string> = {
  "7d": "7d",
  "30d": "30d",
  "90d": "90d",
  all: "All time",
};

export const RANGE_PERIOD_COPY: Record<StatsRange, string> = {
  "7d": "the last 7 days",
  "30d": "the last 30 days",
  "90d": "the last 90 days",
  all: "all time",
};

export const PREVIOUS_RANGE_COPY: Record<StatsRange, string> = {
  "7d": "previous 7 days",
  "30d": "previous 30 days",
  "90d": "previous 90 days",
  all: "previous period",
};

export const EMPTY_STAT_VALUE = "—";
export const PERCENT_SCALE = 100;
export const RATING_MAX = 5;
export const SKELETON_TILE_COUNT = 4;
export const HTTP_NOT_FOUND = 404;

export const CHART_WIDTH = 600;
export const CHART_HEIGHT = 200;
export const CHART_PADDING = 16;
export const CHART_LABEL_GUTTER = 24;
export const CHART_LABEL_BASELINE = CHART_HEIGHT - 6;
export const CHART_GRIDLINE_COUNT = 4;
export const CHART_POINT_RADIUS = 3;
export const BAR_WIDTH_RATIO = 0.7;
export const BAR_LIST_ROW_HEIGHT = 32;
export const BAR_LIST_LABEL_WIDTH = 180;
export const BAR_LIST_VALUE_WIDTH = 120;
export const BAR_LIST_BAR_HEIGHT = 10;

export const TONE_STROKE_CLASSES: Record<ChartTone, string> = {
  neutral: "stroke-content",
  accent: "stroke-accent",
};

export const TONE_FILL_CLASSES: Record<ChartTone, string> = {
  neutral: "fill-content-muted",
  accent: "fill-accent",
};

export const STATS_SECTIONS = {
  plays: { id: "plays", label: "Plays & players" },
  outcomes: { id: "outcomes", label: "Outcomes" },
  engagement: { id: "engagement", label: "Engagement" },
  funnel: { id: "funnel", label: "Funnel & retention" },
  reviews: { id: "reviews", label: "Ratings & reviews" },
  versions: { id: "versions", label: "Versions" },
  benchmarks: { id: "benchmarks", label: "Benchmarks" },
  heatmap: { id: "heatmap", label: "Location heatmap" },
} satisfies Record<string, StatsSectionLink>;

export const SCENARIO_TABLE_COLUMNS: readonly ScenarioTableColumn[] = [
  { key: "title", label: "Scenario" },
  { key: "plays", label: "Plays" },
  { key: "trend", label: "Trend" },
  { key: "completion_rate", label: "Completion" },
  { key: "average_turns", label: "Avg turns" },
  { key: "average_rating", label: "Rating" },
];

export const BENCHMARK_LABELS: Record<BenchmarkKey, string> = {
  completion_rate: "Completion",
  average_turns: "Avg turns",
  average_rating: "Avg rating",
  win_rate: "Win rate",
};

export const BENCHMARK_RATE_KEYS: readonly BenchmarkKey[] = ["completion_rate", "win_rate"];

export const PEER_SCOPE_COPY: Record<PeerScope, string> = {
  genre: "similar stories",
  mode: "stories in the same mode",
};

export const HEATMAP_VIEWBOX_SIZE = 100;
export const HEATMAP_PIN_RADIUS = 2.5;
export const HEATMAP_MIN_OPACITY = 0.15;
