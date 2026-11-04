import { useMutation, useQueryClient } from "@tanstack/react-query";
import { submitSpeechTalk } from "../api/battleSpeech.api";
import { BATTLE_SPEECH_QUERY_ROOT } from "../constants/battleSpeech.constants";
import { buildOperationGuard } from "../lib/operationGuard";
import { parseSimulationError } from "../lib/simulationError";
import { useBattleSpeechStore } from "../stores/battleSpeech.store";
import type { SubmitSpeechTalkInput } from "../types/battleSpeech.types";
import type { CampaignWorldView } from "../types/simulation.types";
import { getWorldQueryKey, readCachedWorld } from "./useSimulationCommands";

const TALK_ERROR = "Could not deliver that talk. Try again.";

export function useSubmitSpeechTalk(playthroughId: string, battleId: string) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: ({ talkIndex, text }: SubmitSpeechTalkInput) =>
      submitSpeechTalk(playthroughId, battleId, {
        guard: buildOperationGuard(readCachedWorld(queryClient, playthroughId)),
        talk_index: talkIndex,
        text,
      }),
    onSuccess: (result) => {
      queryClient.setQueryData<CampaignWorldView>(
        getWorldQueryKey(playthroughId),
        (world) => world && { ...world, ...result.state },
      );
      useBattleSpeechStore.getState().showReaction(result.reaction);
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: [BATTLE_SPEECH_QUERY_ROOT, playthroughId] });
      void queryClient.invalidateQueries({ queryKey: getWorldQueryKey(playthroughId) });
    },
  });
  const errorInfo = mutation.error ? parseSimulationError(mutation.error, TALK_ERROR) : null;
  return {
    submitTalk: mutation.mutate,
    isPending: mutation.isPending,
    result: mutation.data,
    errorInfo,
  };
}
