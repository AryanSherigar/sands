import type {
  ScenarioSummaryResponse,
  ScenarioVisibility,
} from "@/shared/types/scenarioSummary.types";

export type { ScenarioSummaryResponse };

import { SetupInputField } from "@/shared/types/scenario.types";

export interface ScenarioMock {
  id: string;
  title: string;
  logline: string;
  rating: number;
  playerCount: number;
  genre: string;
  author: string;
  coverImageUrl: string;
  setupInputs?: SetupInputField[];
  mode?: "newbie" | "master" | "strategy";
  strategy_document?: Record<string, unknown>;
}

export interface ScenarioDetailResponse extends ScenarioSummaryResponse {
  can_review?: boolean;
  content_tags?: string[];
  creator_avatar_url?: string | null;
  creator_bio?: string | null;
  creator_other_scenarios_count?: number;
  has_maps?: boolean;
  visibility?: ScenarioVisibility;
  has_minigames?: boolean;
  world_data?: Record<string, unknown>;
  setup_schema?: SetupInputField[];
  narrator_persona?: string | null;
  rules?: Record<string, unknown>;
  strategy_document?: Record<string, unknown>;
}

export interface ScenarioReviewResponse {
  review_id: string;
  scenario_id: string;
  user_id: string;
  user_display_name: string;
  rating: number;
  comment: string | null;
  created_at: string;
}

export interface RatingCount {
  stars: number;
  count: number;
}

export interface ScenarioReviewListResponse {
  items: ScenarioReviewResponse[];
  total_count: number;
  average_rating: number;
  rating_counts: RatingCount[];
  own_review: ScenarioReviewResponse | null;
}

export interface PublicPlaythroughSummary {
  playthrough_id: string;
  player_name: string;
  character_name: string | null;
  turn_count: number;
  status: string;
  updated_at: string;
}

export interface FoundEnding {
  ending_id: string | null;
  title: string;
  text: string | null;
  outcome_tag: "win" | "lose" | null;
  turn_reached: number;
  found_at: string;
}

export interface ScenarioEndingsResponse {
  total_count: number;
  found: FoundEnding[] | null;
}
