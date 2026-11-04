import { apiClient } from "@/shared/lib/api-client";
import { SIMULATION_PLAYTHROUGHS_PATH } from "../constants/strategy.constants";
import type {
  SpeechTalkRequest,
  SpeechTalkResult,
  SpeechView,
} from "../types/battleSpeech.types";
import type { OperationGuard } from "../types/simulation.types";

const SIMULATION_REQUEST_CONFIG = { baseURL: "" };

const speechPath = (playthroughId: string, battleId: string): string =>
  `${SIMULATION_PLAYTHROUGHS_PATH}/${playthroughId}/battles/${battleId}/speech`;

export async function getBattleSpeech(playthroughId: string, battleId: string): Promise<SpeechView> {
  const { data } = await apiClient.get<SpeechView>(
    speechPath(playthroughId, battleId),
    SIMULATION_REQUEST_CONFIG,
  );
  return data;
}

export async function submitSpeechTalk(
  playthroughId: string,
  battleId: string,
  request: SpeechTalkRequest,
): Promise<SpeechTalkResult> {
  const { data } = await apiClient.post<SpeechTalkResult>(
    `${speechPath(playthroughId, battleId)}/talks`,
    request,
    SIMULATION_REQUEST_CONFIG,
  );
  return data;
}

export async function skipBattleSpeech(
  playthroughId: string,
  battleId: string,
  guard: OperationGuard,
): Promise<SpeechTalkResult> {
  const { data } = await apiClient.post<SpeechTalkResult>(
    `${speechPath(playthroughId, battleId)}/skip`,
    guard,
    SIMULATION_REQUEST_CONFIG,
  );
  return data;
}
