import { apiClient } from "@/shared/lib/api-client";
import { SIMULATION_PLAYTHROUGHS_PATH } from "../constants/strategy.constants";
import type { MutationResponse, OperationGuard } from "../types/simulation.types";
import type { SceneDecisionInput, SceneViewResponse } from "../types/scene.types";

const SIMULATION_REQUEST_CONFIG = { baseURL: "" };

const scenesPath = (playthroughId: string): string =>
  `${SIMULATION_PLAYTHROUGHS_PATH}/${playthroughId}/scenes`;

export async function openNegotiation(
  playthroughId: string,
  guard: OperationGuard,
  counterpartFactionId: string,
): Promise<MutationResponse> {
  const { data } = await apiClient.post<MutationResponse>(
    `${scenesPath(playthroughId)}/negotiation`,
    { ...guard, counterpart_faction_id: counterpartFactionId },
    SIMULATION_REQUEST_CONFIG,
  );
  return data;
}

export async function getSceneView(
  playthroughId: string,
  sceneId: string,
): Promise<SceneViewResponse> {
  const { data } = await apiClient.get<SceneViewResponse>(
    `${scenesPath(playthroughId)}/${sceneId}`,
    SIMULATION_REQUEST_CONFIG,
  );
  return data;
}

export async function decideScene(
  playthroughId: string,
  sceneId: string,
  guard: OperationGuard,
  input: SceneDecisionInput,
): Promise<MutationResponse> {
  const { data } = await apiClient.post<MutationResponse>(
    `${scenesPath(playthroughId)}/${sceneId}/decision`,
    {
      ...guard,
      is_confirmed: input.isConfirmed,
      proposal_sequence: input.proposalSequence,
    },
    SIMULATION_REQUEST_CONFIG,
  );
  return data;
}
