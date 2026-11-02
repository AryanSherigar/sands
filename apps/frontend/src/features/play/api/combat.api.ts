import { useAuthStore } from "@/features/auth/stores/auth.store";
import { TRS_BASE_URL } from "@/shared/constants/api";
import { buildTrsAuthHeaders } from "@/shared/lib/sse-client";

export interface Combatant {
  actor_id: string;
  side: "player" | "opponent";
  health: number;
  max_health: number;
}

export interface CombatState {
  encounter_id: string;
  revision: number;
  round_number: number;
  status: "active" | "player_defeated" | "opponent_defeated";
  outcome_id: string | null;
  combatants: Combatant[];
  legal_actions: { actor_id: string; action_id: "attack"; target_id: string }[];
}

export interface CombatOptions {
  state: CombatState | null;
  encounters: { encounter_id: string; title: string }[];
}

export interface CombatEvent {
  actor_id: string;
  target_id: string;
  hit: boolean;
  immune: boolean;
  damage: number;
}

export type CombatCommand = {
  path: "start" | "action" | "outcome";
  body: Record<string, unknown>;
};

async function request<T>(path: string, body?: Record<string, unknown>): Promise<T> {
  const response = await fetch(`${TRS_BASE_URL}/v1/combat/${path}`, {
    method: body ? "POST" : "GET",
    headers: { ...buildTrsAuthHeaders(useAuthStore.getState().accessToken), ...(body ? { "Content-Type": "application/json" } : {}) },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  if (!response.ok) throw new Error(`Combat request failed (${response.status})`);
  return (await response.json()) as T;
}

export function fetchCombatOptions(playthroughId: string, participantId: string): Promise<CombatOptions> {
  return request(`${encodeURIComponent(playthroughId)}/options?participant_id=${encodeURIComponent(participantId)}`);
}

export function submitCombat(command: CombatCommand): Promise<CombatState | { state: CombatState; event?: CombatEvent }> {
  return request(command.path, command.body);
}
