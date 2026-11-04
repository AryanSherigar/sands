import { useQuery } from "@tanstack/react-query";
import { getBattleSpeech } from "../api/battleSpeech.api";
import {
  getBattleSpeechQueryKey,
  SPEECH_NOT_FOUND_STATUS,
} from "../constants/battleSpeech.constants";
import { parseSimulationError } from "../lib/simulationError";

const SPEECH_LOAD_ERROR = "Could not load the speech.";

export function useBattleSpeech(playthroughId: string | undefined, battleId: string | null) {
  const query = useQuery({
    queryKey: getBattleSpeechQueryKey(playthroughId, battleId),
    queryFn: () => {
      if (!playthroughId || !battleId) throw new Error(SPEECH_LOAD_ERROR);
      return getBattleSpeech(playthroughId, battleId);
    },
    enabled: Boolean(playthroughId && battleId),
    staleTime: 0,
    retry: false,
  });
  const errorInfo = query.error ? parseSimulationError(query.error, SPEECH_LOAD_ERROR) : null;
  return {
    speech: query.data,
    isSuccess: query.isSuccess,
    isLoading: query.isLoading,
    isUnavailable: errorInfo?.status === SPEECH_NOT_FOUND_STATUS,
    errorInfo,
  };
}
