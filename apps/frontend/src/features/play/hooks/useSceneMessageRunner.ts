import { useCallback, useEffect, useRef, useState } from "react";
import { startSceneMessage, type SceneMessageOptions } from "../lib/scene-stream";

export interface SceneRunOutcome {
  isOk: boolean;
  text: string;
  message: string;
}

const REFUSED_OUTCOME: SceneRunOutcome = { isOk: false, text: "", message: "" };

export const useSceneMessageRunner = (sceneId: string | null) => {
  const [streamedText, setStreamedText] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [failureMessage, setFailureMessage] = useState<string | null>(null);
  const textRef = useRef("");
  const cancelRef = useRef<(() => void) | null>(null);

  const finish = useCallback((): void => {
    cancelRef.current = null;
    setIsStreaming(false);
  }, []);

  const run = useCallback(
    (text: string, options: SceneMessageOptions): Promise<SceneRunOutcome> => {
      if (!sceneId || cancelRef.current) return Promise.resolve(REFUSED_OUTCOME);
      textRef.current = "";
      setStreamedText("");
      setFailureMessage(null);
      setIsStreaming(true);
      return new Promise((resolve) => {
        cancelRef.current = startSceneMessage(
          sceneId,
          text,
          {
            onNarration: (chunk) => {
              textRef.current += chunk;
              setStreamedText(textRef.current);
            },
            onDone: () => {
              finish();
              resolve({ isOk: true, text: textRef.current, message: "" });
            },
            onFailure: (message) => {
              finish();
              setFailureMessage(message);
              resolve({ isOk: false, text: "", message });
            },
          },
          options,
        );
      });
    },
    [sceneId, finish],
  );

  useEffect(
    () => () => {
      cancelRef.current?.();
      cancelRef.current = null;
    },
    [],
  );

  return { streamedText, isStreaming, failureMessage, run };
};
