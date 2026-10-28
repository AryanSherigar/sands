import { useCallback, useEffect, useRef, useState } from "react";
import { startSceneMessage } from "../lib/scene-stream";

export const useSceneStream = (
  sceneId: string | null,
  onExchangeRecorded: () => Promise<unknown>,
) => {
  const [reply, setReply] = useState("");
  const [pendingPlayerText, setPendingPlayerText] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [failureMessage, setFailureMessage] = useState<string | null>(null);
  const replyRef = useRef("");
  const cancelRef = useRef<(() => void) | null>(null);
  const onRecordedRef = useRef(onExchangeRecorded);
  onRecordedRef.current = onExchangeRecorded;

  const resetStream = useCallback((): void => {
    cancelRef.current = null;
    replyRef.current = "";
    setReply("");
    setPendingPlayerText(null);
    setIsStreaming(false);
  }, []);

  const cancel = useCallback((): void => {
    cancelRef.current?.();
    resetStream();
  }, [resetStream]);

  const sendMessage = useCallback(
    (text: string): void => {
      if (!sceneId || cancelRef.current) return;
      replyRef.current = "";
      setReply("");
      setFailureMessage(null);
      setPendingPlayerText(text);
      setIsStreaming(true);
      cancelRef.current = startSceneMessage(sceneId, text, {
        onNarration: (chunk) => {
          replyRef.current += chunk;
          setReply(replyRef.current);
        },
        onDone: () => {
          void onRecordedRef.current().finally(resetStream);
        },
        onFailure: (message) => {
          resetStream();
          setFailureMessage(message);
          void onRecordedRef.current();
        },
      });
    },
    [sceneId, resetStream],
  );

  useEffect(() => cancel, [cancel]);

  return { reply, pendingPlayerText, isStreaming, failureMessage, sendMessage };
};
