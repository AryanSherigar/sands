export interface LifetimeStats {
  turns_taken: number;
  stories_completed: number;
  endings_found: number;
  endings_total: number;
  worlds_played: number;
  campaigns_count: number;
  genres_explored: string[];
}

export interface WeeklyActivity {
  week_start: string;
  played_days: boolean[];
  played_day_count: number;
}

export interface ContinueRun {
  playthrough_id: string;
  scenario_id: string;
  scenario_title: string;
  scenario_mode: "newbie" | "master";
  primary_genre: string | null;
  turn_count: number;
  updated_at: string;
  checkpoint: string | null;
  narration_excerpt: string | null;
}

export interface Milestone {
  key: string;
  name: string;
  earned_at: string;
}

export interface ProfileOverview {
  lifetime_stats: LifetimeStats;
  weekly_activity: WeeklyActivity;
  continue_runs: ContinueRun[];
  recent_milestones: Milestone[];
}
