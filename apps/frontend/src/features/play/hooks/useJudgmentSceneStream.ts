import { useCallback, useRef } from "react";
import type { SceneMessageOptions } from "../lib/scene-stream";
import type { JudgmentPronouncement } from "../types/judgmentScene.types";
import { useSceneMessageRunner } from "./useSceneMessageRunner";

const buildPronounceOptions = (pronouncement: JudgmentPronouncement): SceneMessageOptions => ({
  kind: "pronounce",
  verdict: pronouncement.verdict,
  ...(pronouncement.nuance ? { nuance: pronouncement.nuance } : {}),
});

export const useJudgmentSceneStream = (
  sceneId: string | null,
  onExchangeRecorded: () => Promise<unknown>,
) => {
  const { streamedText, isStreaming, failureMessage, run } = useSceneMessageRunner(sceneId);
  const onRecordedRef = useRef(onExchangeRecorded);
  onRecordedRef.current = onExchangeRecorded;

  const openCourt = useCallback(async (): Promise<string> => {
    const outcome = await run("", { kind: "open" });
    await onRecordedRef.current();
    return outcome.text;
  }, [run]);

  const speak = useCallback(
    async (text: string): Promise<boolean> => {
      const outcome = await run(text, {});
      if (!outcome.isOk) return false;
      await onRecordedRef.current();
      return true;
    },
    [run],
  );

  const pronounce = useCallback(
    async (pronouncement: JudgmentPronouncement): Promise<boolean> => {
      const outcome = await run(pronouncement.decreeText, buildPronounceOptions(pronouncement));
      if (!outcome.isOk) return false;
      await onRecordedRef.current();
      return true;
    },
    [run],
  );

  return { streamedText, isStreaming, failureMessage, openCourt, speak, pronounce };
};
