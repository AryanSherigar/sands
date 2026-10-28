import { apiClient } from "@/shared/lib/api-client";
import { SIMULATION_PLAYTHROUGHS_PATH } from "../constants/strategy.constants";
import type { TurnReportResponse } from "../types/turnReportApi.types";
import type {
  CampaignWorldView,
  EconomyChoice,
  MutationResponse,
  OperationGuard,
  OrderCheckResponse,
  StrategySummaryPage,
  StrategySummaryView,
  StrategyOrder,
  StrategyCommand,
} from "../types/simulation.types";

const SIMULATION_REQUEST_CONFIG = { baseURL: "" };

const playthroughPath = (playthroughId: string): string =>
  `${SIMULATION_PLAYTHROUGHS_PATH}/${playthroughId}`;

export async function getCampaignWorld(playthroughId: string): Promise<CampaignWorldView> {
  const { data } = await apiClient.get<CampaignWorldView>(
    `${playthroughPath(playthroughId)}/world`,
    SIMULATION_REQUEST_CONFIG,
  );
  return data;
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
