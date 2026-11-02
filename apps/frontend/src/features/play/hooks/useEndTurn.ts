import { useMutation, useQueryClient } from "@tanstack/react-query";
import type { QueryClient } from "@tanstack/react-query";
import { advanceBattles, endTurn, getTurnReport } from "../api/simulation.api";
import { MAX_BATTLE_WAVES } from "../constants/strategy.constants";
import { buildOperationGuard } from "../lib/operationGuard";
import { parseSimulationError } from "../lib/simulationError";
import { deriveTurnReport } from "../lib/turnReportAdapter";
import { mergeTurnReport } from "../lib/turnReportMerge";
import { logEvent } from "@/shared/lib/logger";
import { useStrategyPlayStore } from "../stores/strategyPlay.store";
import type {
  CampaignWorldView,
  MutationResponse,
} from "../types/simulation.types";
import type { TurnReportResponse } from "../types/turnReportApi.types";
import { getWorldQueryKey, readCachedWorld } from "./useSimulationCommands";
import { getStrategySummariesQueryKey } from "./useStrategySummaries";

const MISSING_PLAYTHROUGH_MESSAGE = "Playthrough ID is required";

async function resolveTurn(
  playthroughId: string,
  initial: MutationResponse,
): Promise<MutationResponse> {
  let latest = initial;
  for (let wave = 0; wave < MAX_BATTLE_WAVES; wave += 1) {
    if (latest.status !== "awaiting_commands") break;
    if (latest.battles.some((battle) => battle.control_mode === "player" && battle.status !== "resolved")) break;
    latest = await advanceBattles(playthroughId, buildOperationGuard(latest));
  }
  return latest;
}

function buildFallbackWorld(
  base: CampaignWorldView,
  latest: MutationResponse,
): CampaignWorldView {
  return {
    ...base,
    turn: latest.turn,
    wave: latest.wave,
    status: latest.status,
    battles: latest.battles ?? base.battles,
    world_version: latest.world_version,
    world_hash: latest.world_hash,
    orders_remaining: latest.orders_remaining,
    clock: {
      ...base.clock,
      turn: latest.turn,
    },
  };
}

function resolveNextWorld(
  queryClient: QueryClient,
  playthroughId: string,
  previousWorld: CampaignWorldView,
  latest: MutationResponse,
): CampaignWorldView {
  try {
    const cached = readCachedWorld(queryClient, playthroughId);
    if (cached.turn === latest.turn && cached.world_version === latest.world_version) {
      return cached;
    }
  } catch {
    // Cache unpopulated
  }
  return buildFallbackWorld(previousWorld, latest);
}

async function fetchCompletedTurnReport(
  playthroughId: string,
  latest: MutationResponse,
): Promise<TurnReportResponse | null> {
  if (latest.status !== "turn_completed") return null;
  try {
    return (await getTurnReport(playthroughId, Math.max(0, latest.turn - 1))) ?? null;
  } catch {
    logEvent("warning", "strategy_turn_report_fetch_failed", { turn: latest.turn });
    return null;
  }
}

function notifyTurnReport(
  previousWorld: CampaignWorldView,
  nextWorld: CampaignWorldView,
  regionNames: Record<string, string>,
  apiReport: TurnReportResponse | null,
): void {
  const estimated = deriveTurnReport(previousWorld, nextWorld, regionNames);
  const report = apiReport
    ? mergeTurnReport(estimated, apiReport, nextWorld, regionNames)
    : estimated;
  useStrategyPlayStore.getState().setLatestReport(report);
  useStrategyPlayStore.setState({ hasUnreadTurnReport: true });
  if (useStrategyPlayStore.getState().autoShowTurnReport) {
    useStrategyPlayStore.getState().openTurnReport();
  }
}

interface EndTurnParams {
  queryClient: QueryClient;
  playthroughId: string;
  regionNames: Record<string, string>;
}

async function executeEndTurn({
  queryClient,
  playthroughId,
  regionNames,
}: EndTurnParams): Promise<MutationResponse> {
  const previousWorld = readCachedWorld(queryClient, playthroughId);
  const guard = buildOperationGuard(previousWorld);
  if (previousWorld.status === "awaiting_battle_decision") {
    throw new Error("Choose whether to take command or delegate the battle first.");
  }
  const started = previousWorld.status === "awaiting_commands"
    ? await advanceBattles(playthroughId, guard)
    : await endTurn(playthroughId, guard);
  const latest = await resolveTurn(playthroughId, started);
  const nextWorld = resolveNextWorld(queryClient, playthroughId, previousWorld, latest);
  const apiReport = await fetchCompletedTurnReport(playthroughId, latest);
  if (latest.status === "turn_completed") {
    notifyTurnReport(previousWorld, nextWorld, regionNames, apiReport);
  }
  queryClient.setQueryData<CampaignWorldView>(getWorldQueryKey(playthroughId), (current) =>
    current && current.world_version > nextWorld.world_version ? current : nextWorld,
  );
  return latest;
}

export function useEndTurn(
  playthroughId?: string,
  regionNames: Record<string, string> = {},
) {
  const queryClient = useQueryClient();

  const invalidateWorld = () => {
    void queryClient.invalidateQueries({ queryKey: getWorldQueryKey(playthroughId) });
    void queryClient.invalidateQueries({ queryKey: getStrategySummariesQueryKey(playthroughId) });
  };

  const endTurnMutation = useMutation({
    mutationFn: async (): Promise<MutationResponse> => {
      if (!playthroughId) throw new Error(MISSING_PLAYTHROUGH_MESSAGE);
      return executeEndTurn({ queryClient, playthroughId, regionNames });
    },
    onSettled: invalidateWorld,
  });

  const errorInfo = endTurnMutation.error
    ? parseSimulationError(endTurnMutation.error, "Could not end the turn")
    : null;

  return {
    endTurn: endTurnMutation.mutate,
    isEndingTurn: endTurnMutation.isPending,
    lastTurnResult: endTurnMutation.data ?? null,
    errorInfo,
  };
}
