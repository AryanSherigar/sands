import { useEffect, useRef, useState } from "react";
import { prefersReducedMotion } from "@/shared/lib/prefersReducedMotion";
import { useReaderPreferencesStore } from "@/shared/stores/readerPreferences.store";
import { ComposureMinigameProps } from "./ComposureMinigame.types";
import type { ComposureResult } from "./composureEngine";
import {
  CANVAS_SIZE_PX,
  RESOLUTION_BEAT_MS,
  STRIKE_FLASH_MS,
} from "./composurePresets";
import { useComposureLoop } from "./useComposureLoop";

type UiPhase = "instructions" | "playing" | "resolved";

const feedbackLabel = (kind: "hit" | "strike" | undefined): string => {
  if (kind === undefined) return "";
  return kind === "hit" ? "Hit" : "Strike";
};

const range = (count: number): number[] => Array.from({ length: count }, (_, i) => i);

export function ComposureMinigame({
  composureConfig,
  onComplete,
}: ComposureMinigameProps) {
  const reduceSensoryEffects = useReaderPreferencesStore(
    (s) => s.reduceSensoryEffects,
  );
  const isReduced = reduceSensoryEffects || prefersReducedMotion();
  const [uiPhase, setUiPhase] = useState<UiPhase>("instructions");
  const [result, setResult] = useState<ComposureResult | null>(null);
  const [isFlashing, setIsFlashing] = useState(false);
  const completionTimeout = useRef<number | null>(null);
  const flashTimeout = useRef<number | null>(null);
  const { texts } = composureConfig;

  const handleFinish = (finished: ComposureResult): void => {
    setResult(finished);
    setUiPhase("resolved");
    completionTimeout.current = window.setTimeout(
      () => onComplete({ outcome_tag: finished.outcome_tag, score: finished.score }),
      RESOLUTION_BEAT_MS,
    );
  };

  const { canvasRef, run, feedback, isPaused, start } = useComposureLoop(
    composureConfig,
    isReduced,
    handleFinish,
  );

  useEffect(
    () => () => {
      if (completionTimeout.current !== null) window.clearTimeout(completionTimeout.current);
      if (flashTimeout.current !== null) window.clearTimeout(flashTimeout.current);
    },
    [],
  );

  useEffect(() => {
    if (feedback?.kind !== "strike") return;
    setIsFlashing(true);
    flashTimeout.current = window.setTimeout(() => setIsFlashing(false), STRIKE_FLASH_MS);
  }, [feedback]);

  const handleStart = (): void => {
    setUiPhase("playing");
    start();
  };

  const isStrike = feedback?.kind === "strike" && isFlashing;
  const flashClass =
    isStrike && !isReduced ? "shadow-[inset_0_0_160px_rgba(185,28,28,0.75)]" : "";

  return (
    <div
      className={`relative flex h-full w-full flex-col items-center justify-center gap-4 bg-black text-white ${flashClass}`}
    >
      <canvas
        ref={canvasRef}
        width={CANVAS_SIZE_PX}
        height={CANVAS_SIZE_PX}
        aria-label="Composure rhythm"
        className="aspect-square w-[min(80vw,60vh)] max-w-[480px]"
      />

      <div className="flex items-center gap-6 font-mono text-sm">
        <div aria-label={`Streak ${run.streak} of ${composureConfig.beats_to_win}`} role="img" className="flex gap-1.5">
          {range(composureConfig.beats_to_win).map((i) => (
            <span
              key={i}
              className={`h-3 w-3 rounded-full border border-white/60 ${i < run.streak ? "bg-white" : ""}`}
            />
          ))}
        </div>
        <div aria-label={`Strikes ${run.strikes} of ${composureConfig.max_strikes}`} role="img" className="flex gap-1.5">
          {range(composureConfig.max_strikes).map((i) => (
            <span
              key={i}
              className={`h-3 w-3 border border-red-400/80 ${i < run.strikes ? "bg-red-500" : ""}`}
            />
          ))}
        </div>
      </div>

      <p role="status" aria-live="polite" className={isStrike && isReduced ? "border border-red-400 px-3 py-1 text-sm" : "sr-only"}>
        {feedbackLabel(feedback?.kind)}
      </p>

      {uiPhase === "instructions" && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 bg-black/90 p-6 text-center">
          <p className="max-w-md text-base">{texts.instructions}</p>
          <button
            type="button"
            onClick={handleStart}
            className="rounded bg-white px-5 py-2 font-medium text-black"
          >
            {texts.start_text}
          </button>
        </div>
      )}

      {uiPhase === "playing" && isPaused && (
        <div role="status" className="absolute inset-0 flex items-center justify-center bg-black/90 text-lg">
          Paused
        </div>
      )}

      {uiPhase === "resolved" && result && (
        <div role="status" className="absolute inset-0 flex items-center justify-center bg-black/90 p-6 text-center text-xl">
          {result.outcome_tag === "win" ? texts.win_text : texts.lose_text}
        </div>
      )}
    </div>
  );
}
