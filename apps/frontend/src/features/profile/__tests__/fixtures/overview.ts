import type { ContinueRun, ProfileOverview } from "../../types/overview.types";

export const makeRun = (overrides: Partial<ContinueRun> = {}): ContinueRun => ({
  playthrough_id: "pt-1",
  scenario_id: "sc-1",
  scenario_title: "The Grey Ledger",
  scenario_mode: "master",
  primary_genre: "Noir / Detective",
  turn_count: 14,
  updated_at: "2026-10-27T10:00:00Z",
  checkpoint: "Act II: The Slipway",
  narration_excerpt: "Rain slicks the wharf.",
  ...overrides,
});

export const overviewBody: ProfileOverview = {
  lifetime_stats: {
    turns_taken: 12,
    stories_completed: 1,
    endings_found: 1,
    endings_total: 4,
    worlds_played: 2,
    campaigns_count: 3,
    genres_explored: ["Sci-Fi"],
  },
  weekly_activity: {
    week_start: "2026-10-27",
    played_days: [true, false, false, false, false, false, false],
    played_day_count: 1,
  },
  continue_runs: [makeRun()],
  recent_milestones: [],
};
