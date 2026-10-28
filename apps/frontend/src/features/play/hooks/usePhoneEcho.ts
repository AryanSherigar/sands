import { useEffect, useState } from "react";
import { useIsMotionReduced } from "@/shared/hooks/useIsMotionReduced";
import type { PhoneEchoParams } from "@/shared/lib/client-effects/clientEffects.types";
import { isVoiceInputSupported, MicRecorder } from "@/shared/lib/audio/mic-recorder";
import { playBreathing, playEcho } from "@/shared/lib/audio/phone-echo-player";
import { usePlayStore } from "../stores/play.store";

export type PhoneEchoPhase = "idle" | "listening" | "silence" | "playing";

const wait = (ms: number): Promise<void> =>
  new Promise((resolve) => setTimeout(resolve, ms));

const MIC_START_TIMEOUT_MS = 8000;

function withTimeout<T>(promise: Promise<T>, ms: number): Promise<T> {
  return Promise.race([
    promise,
    new Promise<never>((_, reject) =>
      setTimeout(() => reject(new Error("Microphone did not start in time")), ms),
    ),
  ]);
}

async function recordClip(recordMs: number, recorder: MicRecorder): Promise<Blob | null> {
  if (!isVoiceInputSupported()) return null;
  try {
    await withTimeout(recorder.start(), MIC_START_TIMEOUT_MS);
    await wait(recordMs);
    return await recorder.stop();
  } catch (error: unknown) {
    console.warn("Phone echo could not record; playing breathing instead", error);
    recorder.cancel();
    return null;
  }
}

async function runEcho(
  params: PhoneEchoParams,
  isReduced: boolean,
  setPhase: (phase: PhoneEchoPhase) => void,
  recorder: MicRecorder,
): Promise<void> {
  setPhase("listening");
  const clip = isReduced ? null : await recordClip(params.record_ms, recorder);
  if (!clip) {
    await playBreathing(params.record_ms);
    return;
  }
  setPhase("silence");
  await wait(params.delay_ms);
  setPhase("playing");
  await playEcho(clip);
}

// While a `phone_echo` client effect is active: listen to the player for
// `record_ms`, wait `delay_ms`, then play their own voice back processed.
// Without a usable microphone (or with reduced effects) the line only breathes.
export function usePhoneEcho(): PhoneEchoPhase {
  const effect = usePlayStore((s) => s.active_client_effect);
  const finishClientEffect = usePlayStore((s) => s.finishClientEffect);
  const isMotionReduced = useIsMotionReduced();
  const [phase, setPhase] = useState<PhoneEchoPhase>("idle");
  const params = effect?.kind === "phone_echo" ? effect.params : null;

  useEffect(() => {
    if (!params) return undefined;
    const recorder = new MicRecorder();
    let isCurrent = true;
    const setIfCurrent = (next: PhoneEchoPhase) => isCurrent && setPhase(next);
    void runEcho(params, isMotionReduced, setIfCurrent, recorder)
      .catch((error: unknown) => console.warn("Phone echo playback failed", error))
      .finally(() => {
        if (!isCurrent) return;
        setPhase("idle");
        finishClientEffect();
      });
    return () => {
      isCurrent = false;
      recorder.cancel();
    };
  }, [params, isMotionReduced, finishClientEffect]);

  return params ? phase : "idle";
}
