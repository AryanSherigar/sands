import type { ScenarioMode } from "../../types/scenario.types";
import type {
  BenchmarkSection,
  EngagementSection,
  FunnelSection,
  HeatmapMap,
  OutcomesSection,
  ReviewsSection,
  ScenarioStatsResponse,
  VersionRow,
} from "../../types/stats.types";

export interface PlaysPanelProps {
  stats: ScenarioStatsResponse;
}

export interface EngagementPanelProps {
  engagement: EngagementSection;
  isSampleSufficient: boolean;
}

export interface FunnelPanelProps {
  funnel: FunnelSection;
  isSampleSufficient: boolean;
}

export interface OutcomesPanelProps {
  outcomes: OutcomesSection;
  isSampleSufficient: boolean;
}

export interface ReviewsPanelProps {
  reviews: ReviewsSection;
  isSampleSufficient: boolean;
}

export interface VersionsPanelProps {
  versions: VersionRow[];
  mode: ScenarioMode;
}

export interface BenchmarksPanelProps {
  benchmarks: BenchmarkSection;
}

export interface HeatmapPanelProps {
  maps: HeatmapMap[];
}
