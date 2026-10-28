import { useCallback, useEffect, useRef, useState } from "react";
import type { ComposureConfigShape } from "@/shared/types/minigame.types";
import { ComposureAudio, type ComposureAudioPort } from "./composureAudio";
import {
  createAudioClock,
  createPerformanceClock,
  type ComposureClock,
} from "./composureClock";
import { attachComposureControls } from "./composureControls";
import {
  ComposureEngine,
  type ComposureFeedback,
  type ComposureResult,
} from "./composureEngine";
import { INITIAL_RUN, type RunState } from "./composurePhysics";
import { readPalette } from "./composurePresets";
import { drawComposureFrame } from "./composureRenderer";

interface AudioSetup {
  clock: ComposureClock;
  audio: ComposureAudio | null;
}

// Audio is the preferred clock; if the browser has none (or refuses), the game
// still runs as a visual-only beat on the performance clock.
function setUpAudio(config: ComposureConfigShape): AudioSetup {
  const Constructor =
    typeof window === "undefined"
      ? undefined
      : (window.AudioContext ??
        (window as unknown as { webkitAudioContext?: typeof AudioContext })
          .webkitAudioContext);
  if (!Constructor) return { clock: createPerformanceClock(), audio: null };
  try {
    const context = new Constructor();
    void context.resume();
    return {
      clock: createAudioClock(context),
      audio: new ComposureAudio(context, config.audio_profile),
    };
  } catch {
    return { clock: createPerformanceClock(), audio: null };
  }
}

export interface ComposureLoop {
  canvasRef: React.RefObject<HTMLCanvasElement>;
  run: RunState;
  feedback: ComposureFeedback | null;
  isPaused: boolean;
  start: () => void;
}

/**
 * Owns the side effects of a Composure run: the audio context, the animation
 * frame loop, key listeners and the pause on a hidden tab. The rules live in
 * ComposureEngine; this hook only wires it to the browser.
 */
export function useComposureLoop(
  config: ComposureConfigShape,
  isReduced: boolean,
  onFinish: (result: ComposureResult) => void,
): ComposureLoop {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [run, setRun] = useState<RunState>(INITIAL_RUN);
  const [feedback, setFeedback] = useState<ComposureFeedback | null>(null);
  const [isPaused, setIsPaused] = useState(false);
  const cleanupRef = useRef<(() => void) | null>(null);
  const onFinishRef = useRef(onFinish);

  useEffect(() => {
    onFinishRef.current = onFinish;
  }, [onFinish]);

  useEffect(() => () => cleanupRef.current?.(), []);

  const start = useCallback((): void => {
    if (cleanupRef.current) return;
    const { clock, audio } = setUpAudio(config);
    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d") ?? null;
    const palette = readPalette(canvas ?? document.body);
    const engine = new ComposureEngine({
      config,
      clock,
      audio: audio as ComposureAudioPort | null,
      rng: Math.random,
      isReduced,
      onChange: (nextRun, nextFeedback) => {
        setRun(nextRun);
        setFeedback(nextFeedback);
      },
      onFinish: (result) => onFinishRef.current(result),
    });
    engine.start();
    let frame = 0;
    const loop = (): void => {
      engine.tick();
      if (context) drawComposureFrame(context, engine.getView(), palette, isReduced);
      frame = window.requestAnimationFrame(loop);
    };
    frame = window.requestAnimationFrame(loop);
    const detach = attachComposureControls(window, config.keys, (key, stamp) =>
      engine.pressKey(key, stamp),
    );
    const handleVisibilityChange = (): void => {
      if (document.hidden) engine.pause();
      else engine.resume();
      setIsPaused(document.hidden);
    };
    document.addEventListener("visibilitychange", handleVisibilityChange);
    cleanupRef.current = () => {
      window.cancelAnimationFrame(frame);
      detach();
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      audio?.close();
      cleanupRef.current = null;
    };
  }, [config, isReduced]);

  return { canvasRef, run, feedback, isPaused, start };
}
