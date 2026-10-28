interface UserStats {
  campaigns_played_count: number;
  victories_count: number;
  total_turns_taken: number;
  scenarios_authored_count: number;
  total_plays_received: number;
}

export interface UserProfile {
  user_id: string;
  display_name: string;
  bio: string | null;
  avatar_url: string | null;
  banner_url: string | null;
  created_at: string;
  auth_provider_id?: string;
  preferred_genres?: string[];
  onboarding_completed_at?: string | null;
  stats: UserStats;
}

export interface UserProfileUpdatePayload {
  display_name?: string;
  bio?: string | null;
  avatar_url?: string | null;
  banner_url?: string | null;
}

export type { UserPlaythroughSummary } from "@/shared/types/playthroughSummary.types";

export interface UserReviewSummary {
  review_id: string;
  scenario_id: string;
  scenario_title: string;
  rating: number;
  review_text: string | null;
  created_at: string;
}
