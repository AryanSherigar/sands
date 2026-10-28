import { useRef } from "react";
import { getPlaythrough } from "@/shared/api/playthroughs.api";
import { logEvent } from "@/shared/lib/logger";
import { generateClientActionId } from "@/shared/lib/request-id";
import { useTurnStream } from "@/shared/hooks/useTurnStream";
import { usePlaytestStore } from "../stores/playtest.store";

interface PendingAction {
  actionText: string;
  clientActionId: string;
}

export const usePlaytestTurns = () => {
  const playthroughId = usePlaytestStore((state) => state.playthroughId);
  const participantId = usePlaytestStore((state) => state.participantId);
  const appendTurn = usePlaytestStore((state) => state.appendTurn);
  const setState = usePlaytestStore((state) => state.setState);
  const refreshState = (): void => {
    if (!playthroughId) return;
    getPlaythrough(playthroughId)
      .then((playthrough) => {
        if (usePlaytestStore.getState().playthroughId === playthroughId) setState(playthrough.state);
      })
      .catch((error) => logEvent("warning", "playtest_state_refresh_failed", { error: String(error) }));
  };
  const stream = useTurnStream({
    onTurnComplete: (turn) => {
      appendTurn(turn);
      refreshState();
    },
    onStateUpdate: setState,
  });
  const pendingRef = useRef<PendingAction | null>(null);

  const send = (action: PendingAction): void => {
    if (!playthroughId || !participantId) return;
    pendingRef.current = action;
    stream.submitTurn({ playthroughId, participantId, ...action });
  };
  const submitAction = (actionText: string): void =>
    send({ actionText, clientActionId: generateClientActionId() });
  const retryAction = (): void => {
    if (pendingRef.current) send(pendingRef.current);
  };

  return {
    submitAction,
    retryAction,
    cancelTurn: stream.cancelTurn,
    narration: stream.narration,
    isStreaming: stream.isStreaming,
    notice: stream.notice,
    failureMessage: stream.failureMessage,
  };
};
