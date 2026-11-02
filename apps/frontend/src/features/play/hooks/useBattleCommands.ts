import { useCallback, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import type { QueryClient } from "@tanstack/react-query";
import { acceptCommand, advanceBattles } from "../api/simulation.api";
import type {
  MissionTarget,
  StandingPlan,
} from "../components/StrategyWarCouncil/StrategyWarCouncil.types";
import { buildOperationGuard } from "../lib/operationGuard";
import { parseSimulationError } from "../lib/simulationError";
import type { BattleFieldCommand, MutationResponse } from "../types/simulation.types";
import { getBattleQueryKey } from "./useBattle";
import { getBattleReportsQueryKey } from "./useBattleReports";
import { getWorldQueryKey, readCachedWorld } from "./useSimulationCommands";

const COMMAND_FAILED_MESSAGE = "The command could not be delivered. Try again.";

interface BattleCommandTarget {
  playthroughId: string;
  battleId: string;
  factionId: string;
}

function sendBattleCommand(
  queryClient: QueryClient,
  playthroughId: string,
  command: BattleFieldCommand,
): Promise<MutationResponse> {
  const guard = buildOperationGuard(readCachedWorld(queryClient, playthroughId));
  return acceptCommand(playthroughId, command, guard);
}

async function sendPlanAndAdvance(
  queryClient: QueryClient,
  target: BattleCommandTarget,
  plan: StandingPlan,
): Promise<MutationResponse> {
  const placed = await sendBattleCommand(queryClient, target.playthroughId, {
    kind: "set_plan",
    faction_id: target.factionId,
    battle_id: target.battleId,
    plan,
  });
  return advanceBattles(target.playthroughId, buildOperationGuard(placed));
}

export function useBattleCommands(target: BattleCommandTarget) {
  const queryClient = useQueryClient();
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const { playthroughId, battleId, factionId } = target;

  const refreshBattleData = useCallback(async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: getWorldQueryKey(playthroughId) }),
      queryClient.invalidateQueries({ queryKey: getBattleQueryKey(playthroughId, battleId) }),
      queryClient.invalidateQueries({ queryKey: getBattleReportsQueryKey(playthroughId, battleId) }),
    ]);
  }, [queryClient, playthroughId, battleId]);

  const handleFailure = useCallback((error: unknown) => {
    const info = parseSimulationError(error, COMMAND_FAILED_MESSAGE);
    setErrorMessage(info.message);
    if (info.isStaleWorld) void refreshBattleData();
  }, [refreshBattleData]);

  const commitWaveMutation = useMutation({
    mutationFn: (plan: StandingPlan) => sendPlanAndAdvance(queryClient, target, plan),
    onSuccess: refreshBattleData,
    onError: handleFailure,
  });

  const fieldCommandMutation = useMutation({
    mutationFn: (command: BattleFieldCommand) =>
      sendBattleCommand(queryClient, playthroughId, command),
    onSuccess: refreshBattleData,
    onError: handleFailure,
  });

  const runFieldCommand = useCallback(async (command: BattleFieldCommand): Promise<boolean> => {
    setErrorMessage(null);
    try {
      await fieldCommandMutation.mutateAsync(command);
      return true;
    } catch {
      return false;
    }
  }, [fieldCommandMutation]);

  const commitWave = useCallback(async (plan: StandingPlan): Promise<boolean> => {
    setErrorMessage(null);
    try {
      await commitWaveMutation.mutateAsync(plan);
      return true;
    } catch {
      return false;
    }
  }, [commitWaveMutation]);

  const withdraw = useCallback(
    () => runFieldCommand({ kind: "withdraw", faction_id: factionId, battle_id: battleId }),
    [runFieldCommand, factionId, battleId],
  );

  const commitReserves = useCallback(
    () => runFieldCommand({ kind: "commit_reserves", faction_id: factionId, battle_id: battleId }),
    [runFieldCommand, factionId, battleId],
  );

  const reconnoitre = useCallback(
    (subjectFactionId: string, missionTarget: MissionTarget) =>
      runFieldCommand({
        kind: "reconnoitre",
        faction_id: factionId,
        battle_id: battleId,
        subject_faction_id: subjectFactionId,
        target: missionTarget,
      }),
    [runFieldCommand, factionId, battleId],
  );

  return {
    commitWave,
    withdraw,
    commitReserves,
    reconnoitre,
    isCommitting: commitWaveMutation.isPending,
    isSendingCommand: fieldCommandMutation.isPending,
    errorMessage,
    clearError: () => setErrorMessage(null),
  };
}
