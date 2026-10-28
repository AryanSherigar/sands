import { useEffect, useRef, useState } from "react";
import { useLockpickLoop, type LockpickOutcome } from "./useLockpickLoop";
import {
  enterMinigameAudio,
  setLockpickMuted,
  setLockpickVolume,
} from "./lockpickAudio";
import { HUD } from "./HUD";
import { LockpickMinigameProps } from "./LockpickMinigame.types";

type UiPhase = "instructions" | "playing" | "paused" | "resolved";
const RESOLUTION_BEAT_MS = 600;

export function LockpickMinigame({
  lockpickConfig,
  onComplete,
}: LockpickMinigameProps) {
  const [uiPhase, setUiPhase] = useState<UiPhase>("instructions");
  const [muted, setMuted] = useState(false);
  const [volume, setVolume] = useState(0.7);
  const resolvedOutcomeRef = useRef<LockpickOutcome | null>(null);
  const completionTimeoutRef = useRef<number | null>(null);

  const handleInternalComplete = (outcome: LockpickOutcome): void => {
    resolvedOutcomeRef.current = outcome;
    setUiPhase("resolved");
    if (completionTimeoutRef.current !== null) return;
    completionTimeoutRef.current = window.setTimeout(
      () => onComplete(outcome),
      RESOLUTION_BEAT_MS,
    );
  };

  const {
    picksRemaining,
    initialPicks,
    cylindersClicked,
    totalCylinders,
    timeRemainingMs,
    durationMs,
    canvasContainerRef,
    start,
    resume,
    isBroken,
    isPaused,
  } = useLockpickLoop(lockpickConfig, handleInternalComplete);

  useEffect(() => {
    const restoreAudio = enterMinigameAudio();
    return () => {
      restoreAudio();
      if (completionTimeoutRef.current !== null) {
        window.clearTimeout(completionTimeoutRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (uiPhase === "playing" && isPaused) {
      setUiPhase("paused");
    }
  }, [isPaused, uiPhase]);

  const begin = (): void => {
    setUiPhase("playing");
    start();
  };

  const continueGame = (): void => {
    resume();
    setUiPhase("playing");
  };

  const toggleMuted = (): void => {
    setLockpickMuted(!muted);
    setMuted(!muted);
  };

  const resolvedOutcome = resolvedOutcomeRef.current;

  return (
    <div className="relative mx-auto flex w-full max-w-[640px] flex-col items-center gap-3">
      {/* Canvas Mount */}
      <div
        ref={canvasContainerRef}
        className="relative aspect-4/3 w-full overflow-hidden rounded-2xl bg-[#0a0c14] shadow-[0_0_50px_rgba(251,191,36,0.15)] [&_canvas]:h-full [&_canvas]:w-full"
      />

      {/* HUD during gameplay */}
      {uiPhase === "playing" && (
        <HUD
          picksRemaining={picksRemaining}
          initialPicks={initialPicks}
          cylindersClicked={cylindersClicked}
          totalCylinders={totalCylinders}
          timeRemainingMs={timeRemainingMs}
          durationMs={durationMs}
        />
      )}

      {/* Volume & Audio Controls */}
      <div className="absolute right-3 top-3 z-10 flex items-center gap-2 rounded-full bg-black/60 px-3 py-1.5 text-xs text-white backdrop-blur-sm">
        <button
          type="button"
          onClick={toggleMuted}
          aria-label={muted ? "Unmute game audio" : "Mute game audio"}
          className="font-semibold text-zinc-300 hover:text-amber-300"
        >
          {muted ? "Unmute" : "Mute"}
        </button>
        <input
          aria-label="Game audio volume"
          type="range"
          min="0"
          max="1"
          step="0.05"
          value={volume}
          onChange={(e) => {
            const next = Number(e.target.value);
            setVolume(next);
            setLockpickVolume(next);
          }}
          className="h-1.5 w-16 cursor-pointer accent-amber-400"
        />
      </div>

      {/* Instructions Phase */}
      {uiPhase === "instructions" && (
        <div className="absolute inset-0 z-20 flex items-center justify-center bg-slate-950/90 p-5 text-center text-white">
          <div className="max-w-md space-y-4">
            <p className="text-xs font-bold uppercase tracking-[0.25em] text-amber-400">
              Lockpick Challenge
            </p>
            <h2 className="text-3xl font-bold">Pick the Lock</h2>
            <p className="text-sm text-slate-300">
              {lockpickConfig.copy?.instructions ??
                "Align your pick with the oscillating sweet spot and hold steady to engage each tumbler. Holding outside under tension will break your pick."}
            </p>
            <div className="grid grid-cols-2 gap-2 text-xs text-slate-400">
              <span className="rounded bg-white/5 p-2">
                Click & Drag Mouse or A / D keys to turn pick
              </span>
              <span className="rounded bg-white/5 p-2">
                Hold in golden zone to click tumblers
              </span>
            </div>
            <button
              type="button"
              onClick={begin}
              className="rounded-lg bg-amber-400 px-6 py-3 font-bold text-slate-950 transition hover:bg-amber-300 focus:outline-hidden focus:ring-2 focus:ring-amber-200"
            >
              {lockpickConfig.copy?.start_text ?? "Begin"}
            </button>
          </div>
        </div>
      )}

      {/* Paused Phase */}
      {uiPhase === "paused" && (
        <div className="absolute inset-0 z-20 flex items-center justify-center bg-slate-950/85 p-5 text-center text-white">
          <div className="space-y-3">
            <h2 className="text-3xl font-bold">Paused</h2>
            <p className="text-sm text-slate-300">
              Focus left the lock. No time passed while paused.
            </p>
            <button
              type="button"
              onClick={continueGame}
              className="rounded-lg bg-amber-400 px-6 py-3 font-bold text-slate-950 hover:bg-amber-300"
            >
              Resume
            </button>
          </div>
        </div>
      )}

      {/* Pick Break Flash Effect */}
      {uiPhase === "playing" && isBroken && (
        <div
          role="status"
          className="pointer-events-none absolute inset-0 animate-pulse border-4 border-rose-500/80"
          aria-label="Pick broken!"
        />
      )}

      {/* Resolved Phase */}
      {uiPhase === "resolved" && resolvedOutcome && (
        <div className="pointer-events-none absolute inset-0 z-20 flex items-center justify-center bg-slate-950/85 p-6 text-center text-white">
          <div className="space-y-2">
            <p className="text-4xl font-bold">
              {resolvedOutcome.outcome_tag === "win"
                ? (lockpickConfig.copy?.win_text ?? "Unlocked!")
                : (lockpickConfig.copy?.lose_text ?? "Pick broken.")}
            </p>
            <p className="text-sm text-amber-300">
              {resolvedOutcome.outcome_tag === "win"
                ? `Picks preserved: ${resolvedOutcome.score}`
                : "The lock held fast."}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
