import { apiClient } from "@/shared/lib/api-client";
import { generateClientActionId } from "@/shared/lib/request-id";
import type { StrategyArtKind, StrategyArtView } from "../types/strategyArt.types";

const TRS_REQUEST_CONFIG = { baseURL: "" };

export const getStrategyArtPath = (playthroughId: string): string =>
  `/trs/v1/strategy/playthroughs/${playthroughId}/art`;

export async function requestStrategyArt(
  playthroughId: string,
  kind: StrategyArtKind,
  itemId: string,
): Promise<StrategyArtView> {
  const { data } = await apiClient.post<StrategyArtView>(
    getStrategyArtPath(playthroughId),
    { kind, item_id: itemId, client_request_id: generateClientActionId() },
    TRS_REQUEST_CONFIG,
  );
  return data;
}
