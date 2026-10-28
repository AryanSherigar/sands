import { useCallback, useEffect, useRef, useState } from "react";
import {
  startNarrativeTurn,
  type NarrativeTurnRequest,
} from "../lib/turn-stream";

interface CompletedTurn {
  actionText: string;
  narration: string;
}

interface UseTurnStreamOptions {
  onTurnComplete: (turn: CompletedTurn) => void;
  onStateUpdate?: (state: Record<string, unknown>) => void;
}

export const useTurnStream = ({ onTurnComplete, onStateUpdate }: UseTurnStreamOptions) => {
  const [narration, setNarration] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [failureMessage, setFailureMessage] = useState<string | null>(null);
  const narrationRef = useRef("");
  const cancelRef = useRef<(() => void) | null>(null);
  const onCompleteRef = useRef(onTurnComplete);
  onCompleteRef.current = onTurnComplete;
  const onStateUpdateRef = useRef(onStateUpdate);
  onStateUpdateRef.current = onStateUpdate;

  const resetStream = useCallback((): void => {
    cancelRef.current = null;
    narrationRef.current = "";
    setNarration("");
    setIsStreaming(false);
  }, []);

  const stop = useCallback((): void => {
    cancelRef.current?.();
    resetStream();
  }, [resetStream]);

  const submitTurn = useCallback(
    (request: NarrativeTurnRequest): void => {
      if (cancelRef.current) return;
      narrationRef.current = "";
      setNarration("");
      setNotice(null);
      setFailureMessage(null);
      setIsStreaming(true);
      cancelRef.current = startNarrativeTurn(request, {
        onNarration: (chunk) => {
          narrationRef.current += chunk;
          setNarration(narrationRef.current);
        },
        onNotice: setNotice,
        onStateUpdate: (state) => onStateUpdateRef.current?.(state),
        onDone: () => {
          const finished = narrationRef.current;
          resetStream();
          onCompleteRef.current({ actionText: request.actionText, narration: finished });
        },
        onFailure: (message) => {
          resetStream();
          setFailureMessage(message);
        },
      });
    },
    [resetStream],
  );

  useEffect(() => stop, [stop]);

  return { narration, isStreaming, notice, failureMessage, submitTurn, cancelTurn: stop };
};
