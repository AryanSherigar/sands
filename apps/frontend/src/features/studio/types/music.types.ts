import { ScenarioMood } from "@/shared/types/audio.types";

type MusicSource = "upload" | "generated" | "default";

export interface ScenarioMusicSlot {
  scenario_music_id: string;
  scenario_id: string;
  mood: ScenarioMood;
  source: MusicSource;
  track_url: string | null;
  generation_prompt: string | null;
  key: string | null;
  bpm: number | null;
  duration_seconds: number | null;
  created_at: string;
  updated_at: string;
}

export interface ScenarioMusicListResponse {
  items: ScenarioMusicSlot[];
}
