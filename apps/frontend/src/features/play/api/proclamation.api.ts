import { apiClient } from "@/shared/lib/api-client";
import { TRS_BASE_URL } from "@/shared/constants/api";
import { SIMULATION_PLAYTHROUGHS_PATH } from "../constants/strategy.constants";
import type { OperationGuard } from "../types/simulation.types";
import { createPostSSEConnection } from "@/shared/lib/sse-client";
import { useAuthStore } from "@/features/auth/stores/auth.store";

export interface ProclamationDraft {
  is_recognized: boolean;
  domain: string;
  burden: string;
  target_estate?: string | null;
  concession_estate?: string | null;
  legal_summary: string;
  fallback_reason?: string | null;
}

export interface ProclamationMinisterView {
  estate: string;
  title: string;
  stance: "support" | "cautious" | "oppose";
  primary_grievance: string;
}

export interface ProclamationScenePackage {
  scene_id: string;
  draft: ProclamationDraft;
  ministers: ProclamationMinisterView[];
  exchange_cap: number;
  is_rescinding_previous: boolean;
}

export interface ActiveProclamation {
  id: string;
  legal_summary: string;
  domain: string;
  burden: string;
  enacted_turn: number;
  remaining_turns: number;
  immediate_deltas: Record<string, number>;
  ongoing_modifiers: Record<string, number>;
}

const SIMULATION_REQUEST_CONFIG = { baseURL: "" };
const TRS_PROCLAMATION_PATH = "/v1/strategy/proclamation";

export async function classifyProclamation(text: string): Promise<ProclamationDraft> {
  const { data } = await apiClient.post<ProclamationDraft>(
    `${TRS_BASE_URL}${TRS_PROCLAMATION_PATH}/classify`,
    { text },
    SIMULATION_REQUEST_CONFIG
  );
  return data;
}

export async function conveneProclamationCouncil(
  playthroughId: string,
  draft: ProclamationDraft,
  isRescindingPrevious: boolean = false
): Promise<ProclamationScenePackage> {
  const { data } = await apiClient.post<ProclamationScenePackage>(
    `${SIMULATION_PLAYTHROUGHS_PATH}/${playthroughId}/proclamation/convene`,
    { draft, is_rescinding_previous: isRescindingPrevious },
    SIMULATION_REQUEST_CONFIG
  );
  return data;
}

export async function decideProclamation(
  playthroughId: string,
  guard: OperationGuard,
  draft: ProclamationDraft,
  verdict: "fiat" | "compromise",
  isRescindingPrevious: boolean = false
): Promise<ActiveProclamation> {
  const { data } = await apiClient.post<ActiveProclamation>(
    `${SIMULATION_PLAYTHROUGHS_PATH}/${playthroughId}/proclamation/decision`,
    {
      guard,
      draft,
      verdict,
      is_rescinding_previous: isRescindingPrevious,
    },
    SIMULATION_REQUEST_CONFIG
  );
  return data;
}

export function streamCouncilDialogue(
  draft: ProclamationDraft,
  turnContext: Record<string, unknown>,
  playerSpeech?: string,
  callbacks?: {
    onChunk?: (text: string) => void;
    onDone?: () => void;
    onError?: (err: unknown) => void;
  }
): () => void {
  const url = `${TRS_BASE_URL}${TRS_PROCLAMATION_PATH}/narrate`;
  const body = { draft, turn_context: turnContext, player_speech: playerSpeech };
  return createPostSSEConnection(url, body, useAuthStore.getState().accessToken, {
    onEvent: (event, data) => {
      if (event === "narration") {
        callbacks?.onChunk?.(data);
      } else if (event === "done") {
        callbacks?.onDone?.();
      }
    },
    onError: callbacks?.onError,
  });
}
