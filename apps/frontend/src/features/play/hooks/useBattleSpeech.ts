import { useCallback, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { postBattleSpeech } from "../api/simulation.api";
import { requestSpeechReaction } from "../api/strategyBattleSpeech.api";
import { buildOperationGuard } from "../lib/operationGuard";
import { parseSimulationError } from "../lib/simulationError";
import type { SpeechReception } from "../types/simulation.types";
import { getBattleQueryKey } from "./useBattle";
import { getWorldQueryKey, readCachedWorld } from "./useSimulationCommands";

const SPEECH_FAILED_MESSAGE = "Your words did not reach the ranks. Try again, or say nothing.";

export function useBattleSpeech(playthroughId: string, battleId: string) {
  const queryClient = useQueryClient();
  const [reception, setReception] = useState<SpeechReception | null>(null);
  const [reactionLine, setReactionLine] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSending, setIsSending] = useState(false);

  const address = useCallback(
    async (speechText: string): Promise<boolean> => {
      setErrorMessage(null);
      setIsSending(true);
      try {
        const guard = buildOperationGuard(readCachedWorld(queryClient, playthroughId));
        const response = await postBattleSpeech(playthroughId, battleId, speechText, guard);
        setReception(response.reception);
        void requestSpeechReaction(playthroughId, battleId).then(setReactionLine);
        await Promise.all([
          queryClient.invalidateQueries({ queryKey: getWorldQueryKey(playthroughId) }),
          queryClient.invalidateQueries({ queryKey: getBattleQueryKey(playthroughId, battleId) }),
        ]);
        return true;
      } catch (error) {
        setErrorMessage(parseSimulationError(error, SPEECH_FAILED_MESSAGE).message);
        return false;
      } finally {
        setIsSending(false);
      }
    },
    [queryClient, playthroughId, battleId],
  );

  return { address, reception, reactionLine, errorMessage, isSending };
}
