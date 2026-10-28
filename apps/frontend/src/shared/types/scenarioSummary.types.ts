import type { ComplexityTier } from "@/shared/constants/complexity-tiers";

export type ScenarioMode = "newbie" | "master" | "strategy";
type PlaytimeBucket = "short" | "medium" | "long";
export type ScenarioVisibility = "public" | "private";
export type ScenarioSortField = "created_at" | "play_count" | "rating_avg";

export interface ScenarioSummaryResponse {
  scenario_id: string;
  creator_id: string;
  creator_display_name: string | null;
  is_bookmarked: boolean;
  title: string;
  logline: string | null;
  mode: ScenarioMode;
  status: "draft" | "publishing" | "published" | "publish_failed" | "archived";
  genre_tags: string[];
  complexity_tier: ComplexityTier;
  player_count_support: "solo" | "multiplayer" | "both";
  estimated_playtime: string | null;
  playtime_bucket: PlaytimeBucket | null;
  is_mature: boolean;
  cover_image_url: string | null;
  content_tag: string | null;
  play_count: number;
  rating_avg: string;
  created_at: string;
  updated_at: string;
}

export interface ScenarioListResponse {
  items: ScenarioSummaryResponse[];
  next_cursor: string | null;
  total_count: number;
}

export interface GetScenariosParams {
  creator_id?: string;
  mine?: boolean;
  saved?: boolean;
  played?: boolean;
  genre_tags?: string[];
  complexity_tier?: ComplexityTier;
  player_count_support?: "solo" | "multiplayer" | "both";
  mode?: ScenarioMode;
  playtime_bucket?: PlaytimeBucket;
  q?: string;
  include_mature?: boolean;
  sort?: ScenarioSortField;
  limit?: number;
  offset?: number;
}
