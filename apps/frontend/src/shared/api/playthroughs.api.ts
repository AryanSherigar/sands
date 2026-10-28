import { apiClient } from "@/shared/lib/api-client";
import type { RuleSheetItem } from "@/shared/types/rule-sheet.types";
import type { UserPlaythroughSummary } from "@/shared/types/playthroughSummary.types";

export const fetchUserPlaythroughs = async (
  status?: string,
): Promise<UserPlaythroughSummary[]> => {
  const { data } = await apiClient.get<UserPlaythroughSummary[]>(
    "/v1/users/me/playthroughs",
    { params: status ? { status } : undefined },
  );
  return data;
};

export interface PlayerRulerPayload {
  name: string;
  epithet?: string | null;
  portrait_url?: string | null;
  trait_ids: string[];
  ambition_ids: string[];
  backstory?: string;
}

export interface CreatePlaythroughPayload {
  scenario_id: string;
  setup_values?: Record<string, unknown>;
  faction_id?: string;
  player_ruler?: PlayerRulerPayload;
}

export interface ParticipantSummary {
  participant_id: string;
  user_id: string;
  role: "owner" | "joined";
  turn_order_position: number;
}

export interface PlaythroughResponse {
  playthrough_id: string;
  scenario_id: string;
  scenario_title: string;
  created_by: string;
  state: Record<string, unknown>;
  checkpoint: string | null;
  turn_count: number;
  status: string;
  scenario_version: number;
  scenario_snapshot: Record<string, unknown>;
  // The server clock when this response was built, used to work out how much
  // time is left on a timed prompt that was open when the page loaded.
  server_time_ms: number;
  rule_sheet?: RuleSheetItem[];
  created_at: string;
  updated_at: string;
  // The requesting user's own participant_id — required by POST /v1/turn.
  participant_id: string;
  participants: ParticipantSummary[];
  // Master-mode-only; [] for newbie or no scenario_conditions currently true.
  active_conditions: string[];
  // Populated once an end condition matches (status becomes "completed").
  ended_outcome_tag: "win" | "lose" | null;
  ended_outcome_title: string | null;
  ended_outcome_text: string | null;
}

export async function createPlaythrough(
  payload: CreatePlaythroughPayload,
): Promise<PlaythroughResponse> {
  const response = await apiClient.post<PlaythroughResponse>(
    "/v1/playthroughs",
    payload,
  );
  return response.data;
}

export async function getPlaythrough(
  playthroughId: string,
): Promise<PlaythroughResponse> {
  const response = await apiClient.get<PlaythroughResponse>(
    `/v1/playthroughs/${playthroughId}`,
  );
  return response.data;
}

export async function startPlaytest(
  scenarioId: string,
  setupValues: Record<string, unknown> = {},
  stateOverrides: Record<string, unknown> = {},
): Promise<PlaythroughResponse> {
  const hasOverrides = Object.keys(stateOverrides).length > 0;
  const response = await apiClient.post<PlaythroughResponse>(
    `/v1/scenarios/${scenarioId}/playtest`,
    {
      setup_values: setupValues,
      ...(hasOverrides ? { state_overrides: stateOverrides } : {}),
    },
  );
  return response.data;
}
