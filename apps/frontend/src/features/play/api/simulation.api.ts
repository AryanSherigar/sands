import { apiClient } from "@/shared/lib/api-client";
import { SIMULATION_PLAYTHROUGHS_PATH } from "../constants/strategy.constants";
import type {
  BattleView,
  ExchangeReport,
} from "../components/StrategyWarCouncil/StrategyWarCouncil.types";
import { parseCampaignWorld } from "../lib/campaignWorldParser";
import { adaptHistoricalWorld } from "../lib/historicalWorld";
import type { TurnReportResponse } from "../types/turnReportApi.types";
import type {
  BattleSpeechResponse,
  CampaignWorldView,
  EconomyChoice,
  MutationResponse,
  OperationGuard,
  OrderCheckResponse,
  StrategyDispatchView,
  StrategySummaryPage,
  StrategySummaryView,
  StrategyOrder,
  StrategyCommand,
} from "../types/simulation.types";

const SIMULATION_REQUEST_CONFIG = { baseURL: "" };

const playthroughPath = (playthroughId: string): string =>
  `${SIMULATION_PLAYTHROUGHS_PATH}/${playthroughId}`;

export async function getCampaignWorld(playthroughId: string): Promise<CampaignWorldView> {
  const { data } = await apiClient.get<unknown>(
    `${playthroughPath(playthroughId)}/world`,
    SIMULATION_REQUEST_CONFIG,
  );
  return parseCampaignWorld(data);
}

export async function checkCommand(
  playthroughId: string,
  command: StrategyOrder,
): Promise<OrderCheckResponse> {
  const { data } = await apiClient.post<OrderCheckResponse>(
    `${playthroughPath(playthroughId)}/commands/check`,
    { command },
    SIMULATION_REQUEST_CONFIG,
  );
  return data;
}

export async function acceptCommand(
  playthroughId: string,
  command: StrategyCommand,
  guard: OperationGuard,
): Promise<MutationResponse> {
  const { data } = await apiClient.post<MutationResponse>(
    `${playthroughPath(playthroughId)}/commands`,
    { ...guard, command },
    SIMULATION_REQUEST_CONFIG,
  );
  return data;
}

export async function cancelCommand(
  playthroughId: string,
  commandId: string,
  guard: OperationGuard,
): Promise<MutationResponse> {
  const { data } = await apiClient.post<MutationResponse>(
    `${playthroughPath(playthroughId)}/commands/${commandId}/cancel`,
    guard,
    SIMULATION_REQUEST_CONFIG,
  );
  return data;
}

export async function chooseEconomyOutcome(
  playthroughId: string,
  sceneId: string,
  choice: EconomyChoice,
  guard: OperationGuard,
): Promise<MutationResponse> {
  const { data } = await apiClient.post<MutationResponse>(
    `${playthroughPath(playthroughId)}/scenes/${sceneId}/choice`,
    { ...guard, choice },
    SIMULATION_REQUEST_CONFIG,
  );
  return data;
}

export async function endTurn(
  playthroughId: string,
  guard: OperationGuard,
): Promise<MutationResponse> {
  const { data } = await apiClient.post<MutationResponse>(
    `${playthroughPath(playthroughId)}/end-turn`,
    guard,
    SIMULATION_REQUEST_CONFIG,
  );
  return data;
}

export async function advanceBattles(
  playthroughId: string,
  guard: OperationGuard,
): Promise<MutationResponse> {
  const { data } = await apiClient.post<MutationResponse>(
    `${playthroughPath(playthroughId)}/battles/advance`,
    guard,
    SIMULATION_REQUEST_CONFIG,
  );
  return data;
}

export async function getTurnReport(
  playthroughId: string,
  turn: number,
): Promise<TurnReportResponse> {
  const { data } = await apiClient.get<TurnReportResponse>(
    `${playthroughPath(playthroughId)}/turns/${turn}/report`,
    SIMULATION_REQUEST_CONFIG,
  );
  return data;
}

export async function getStrategySummaries(
  playthroughId: string,
): Promise<StrategySummaryPage> {
  const { data } = await apiClient.get<StrategySummaryPage>(
    `${playthroughPath(playthroughId)}/summaries`,
    SIMULATION_REQUEST_CONFIG,
  );
  return data;
}

export async function getStrategySummary(
  playthroughId: string,
  summaryId: string,
): Promise<StrategySummaryView> {
  const { data } = await apiClient.get<StrategySummaryView>(
    `${playthroughPath(playthroughId)}/summaries/${summaryId}`,
    SIMULATION_REQUEST_CONFIG,
  );
  return data;
}

export const getStrategySummaryStreamPath = (
  playthroughId: string,
  summaryId: string,
): string => `/trs/v1/strategy/playthroughs/${playthroughId}/summaries/${summaryId}/stream`;

export async function getStrategyDispatches(
  playthroughId: string,
): Promise<StrategyDispatchView[]> {
  const { data } = await apiClient.get<StrategyDispatchView[]>(
    `${playthroughPath(playthroughId)}/dispatches`,
    SIMULATION_REQUEST_CONFIG,
  );
  return data;
}

export const getStrategyDispatchStreamPath = (
  playthroughId: string,
  rumorId: string,
): string => `/trs/v1/strategy/playthroughs/${playthroughId}/dispatches/${rumorId}/stream`;

export async function getBattle(
  playthroughId: string,
  battleId: string,
): Promise<BattleView> {
  const { data } = await apiClient.get<BattleView>(
    `${playthroughPath(playthroughId)}/battles/${battleId}`,
    SIMULATION_REQUEST_CONFIG,
  );
  return data;
}

export async function listBattleReports(
  playthroughId: string,
  battleId: string,
  afterExchange = 0,
  limit = 50,
): Promise<ExchangeReport[]> {
  const { data } = await apiClient.get<{ items?: ExchangeReport[] } | ExchangeReport[]>(
    `${playthroughPath(playthroughId)}/battles/${battleId}/reports?after_exchange=${afterExchange}&limit=${limit}`,
    SIMULATION_REQUEST_CONFIG,
  );
  if (Array.isArray(data)) {
    return data;
  }
  return data.items ?? [];
}

export interface ReplayVerificationResponse {
  verified_turn: number;
  world_hash: string;
  step_count: number;
}

export async function postBattleSpeech(
  playthroughId: string,
  battleId: string,
  speechText: string,
  guard: OperationGuard,
): Promise<BattleSpeechResponse> {
  const { data } = await apiClient.post<BattleSpeechResponse>(
    `${playthroughPath(playthroughId)}/battles/${battleId}/speech`,
    { ...guard, speech_text: speechText },
    SIMULATION_REQUEST_CONFIG,
  );
  return data;
}

export async function getHistoricalWorld(
  playthroughId: string,
  turn: number,
): Promise<CampaignWorldView> {
  const { data } = await apiClient.get<Parameters<typeof adaptHistoricalWorld>[0]>(
    `${playthroughPath(playthroughId)}/history/${turn}`,
    SIMULATION_REQUEST_CONFIG,
  );
  return adaptHistoricalWorld(data);
}

export async function verifyPlaythroughReplay(
  playthroughId: string,
  throughTurn?: number,
): Promise<ReplayVerificationResponse> {
  const query = throughTurn !== undefined ? `?through_turn=${throughTurn}` : "";
  const { data } = await apiClient.post<ReplayVerificationResponse>(
    `${playthroughPath(playthroughId)}/replay/verify${query}`,
    undefined,
    SIMULATION_REQUEST_CONFIG,
  );
  return data;
}
