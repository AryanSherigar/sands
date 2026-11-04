import { useMutation, useQueryClient } from "@tanstack/react-query";
import { skipBattleSpeech } from "../api/battleSpeech.api";
import { BATTLE_SPEECH_QUERY_ROOT } from "../constants/battleSpeech.constants";
import { buildOperationGuard } from "../lib/operationGuard";
import { parseSimulationError } from "../lib/simulationError";
import { useBattleSpeechStore } from "../stores/battleSpeech.store";
import type { CampaignWorldView } from "../types/simulation.types";
import { getWorldQueryKey, readCachedWorld } from "./useSimulationCommands";

const SKIP_ERROR = "Could not skip the speech. Try again.";

export function useSkipBattleSpeech(playthroughId: string, battleId: string) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: () =>
      skipBattleSpeech(playthroughId, battleId, buildOperationGuard(readCachedWorld(queryClient, playthroughId))),
    onSuccess: (result) => {
      queryClient.setQueryData<CampaignWorldView>(
        getWorldQueryKey(playthroughId),
        (world) => world && { ...world, ...result.state },
      );
      useBattleSpeechStore.getState().reset();
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: [BATTLE_SPEECH_QUERY_ROOT, playthroughId] });
      void queryClient.invalidateQueries({ queryKey: getWorldQueryKey(playthroughId) });
    },
  });
  const errorInfo = mutation.error ? parseSimulationError(mutation.error, SKIP_ERROR) : null;
  return { skip: mutation.mutate, isPending: mutation.isPending, errorInfo };
}
