import { useCallback, useEffect, useRef, useState } from "react";
import { startSceneMessage, type SceneMessageOptions } from "../lib/scene-stream";

interface StreamOutcome {
  isOk: boolean;
  text: string;
  message: string;
}

const REFUSED_OUTCOME: StreamOutcome = { isOk: false, text: "", message: "" };

export const useLetterSceneStream = (
  sceneId: string | null,
  onExchangeRecorded: () => Promise<unknown>,
) => {
  const [streamedText, setStreamedText] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [failureMessage, setFailureMessage] = useState<string | null>(null);
  const textRef = useRef("");
  const cancelRef = useRef<(() => void) | null>(null);
  const onRecordedRef = useRef(onExchangeRecorded);
  onRecordedRef.current = onExchangeRecorded;

  const finish = useCallback((): void => {
    cancelRef.current = null;
    setIsStreaming(false);
  }, []);

  const run = useCallback(
    (text: string, options: SceneMessageOptions): Promise<StreamOutcome> => {
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

  const openLetter = useCallback(async (): Promise<string> => {
    const outcome = await run("", { kind: "open" });
    await onRecordedRef.current();
    return outcome.text;
  }, [run]);

  const requestScribeDraft = useCallback(
    async (instruction: string, currentDraft: string): Promise<string> => {
      const outcome = await run(instruction, { kind: "scribe", currentDraft });
      if (!outcome.isOk) throw new Error(outcome.message);
      return outcome.text;
    },
    [run],
  );

  const sealLetter = useCallback(
    async (prose: string): Promise<boolean> => {
      const outcome = await run(prose, { kind: "seal" });
      if (!outcome.message && !outcome.isOk) return false;
      await onRecordedRef.current();
      return outcome.isOk;
    },
    [run],
  );

  useEffect(
    () => () => {
      cancelRef.current?.();
      cancelRef.current = null;
    },
    [],
  );

  return {
    streamedText,
    isStreaming,
    failureMessage,
    openLetter,
    requestScribeDraft,
    sealLetter,
  };
};
