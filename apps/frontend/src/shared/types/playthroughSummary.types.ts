export interface UserPlaythroughSummary {
  playthrough_id: string;
  scenario_id: string;
  scenario_title: string;
  scenario_mode: "newbie" | "master" | "strategy";
  cover_image_url: string | null;
  turn_count: number;
  status: "active" | "completed" | "abandoned";
  ended_outcome_tag: "win" | "lose" | null;
  ended_outcome_title: string | null;
  ended_outcome_text: string | null;
  character_name: string | null;
  character_archetype: string | null;
  created_at: string;
  updated_at: string;
}
