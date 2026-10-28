import { useEffect, useRef, useState } from "react";
import { Application } from "pixi.js";
import {
  LOCK_CANVAS_HEIGHT,
  LOCK_CANVAS_WIDTH,
  LOCK_CENTER_X,
  LOCK_CENTER_Y,
  getLockpickPreset,
} from "./lockpickPresets";
import {
  advanceSimulation,
  createInitialSimState,
  isInSweetSpot,
} from "./lockpickPhysics";
import {
  calculateAngleFromCenter,
  computeNextPickAngle,
  createInitialControllerState,
} from "./lockpickController";
import { createLockScene } from "./scene/lock";
import { createNeedleScene } from "./scene/needle";
import { createCylindersScene } from "./scene/cylinders";
import {
  playCylinderClick,
  playDwellTick,
  playLoseStinger,
  playPickBreakSfx,
  playWinStinger,
} from "./lockpickAudio";
import type { LockpickConfigShape } from "@/shared/types/minigame.types";

export interface LockpickOutcome {
  outcome_tag: "win" | "lose" | "timeout";
  score: number;
}

export interface UseLockpickLoopResult {
  picksRemaining: number;
  initialPicks: number;
  cylindersClicked: number;
  totalCylinders: number;
  timeRemainingMs: number;
  durationMs: number;
  canvasContainerRef: React.RefObject<HTMLDivElement>;
  start: () => void;
  pause: () => void;
  resume: () => void;
  isBroken: boolean;
  isPaused: boolean;
}

const DEFAULT_MINIGAME_DURATION_MS = 30_000;
const DWELL_TICK_INTERVAL_MS = 120;

export function useLockpickLoop(
  lockpickConfig: LockpickConfigShape,
  onComplete: (outcome: LockpickOutcome) => void,
): UseLockpickLoopResult {
  const preset = getLockpickPreset(lockpickConfig.difficulty);
  const initialPicks = lockpickConfig.picks ?? 3;
  const durationMs = DEFAULT_MINIGAME_DURATION_MS;

  const containerRef = useRef<HTMLDivElement>(null);
  const startRef = useRef<() => void>(() => {});
  const pauseRef = useRef<() => void>(() => {});
  const resumeRef = useRef<() => void>(() => {});

  const [picksRemaining, setPicksRemaining] = useState(initialPicks);
  const [cylindersClicked, setCylindersClicked] = useState(0);
  const [timeRemainingMs, setTimeRemainingMs] = useState(durationMs);
  const [isBroken, setIsBroken] = useState(false);
  const [isPaused, setIsPaused] = useState(false);

  const onCompleteRef = useRef(onComplete);
  onCompleteRef.current = onComplete;

  useEffect(() => {
    if (!containerRef.current) return undefined;
    const mountEl = containerRef.current;
    let destroyed = false;
    let isInitialized = false;
    const app = new Application();

    let isPlaying = false;
    let isPausedLocal = false;
    let hasResolved = false;
    let lastDwellTickTime = 0;
    let breakFlashTimer: number | null = null;

    let simState = createInitialSimState(initialPicks, 180, 90);
    const controller = createInitialControllerState();
    let elapsedMs = 0;

    const resolve = (outcome: LockpickOutcome): void => {
      if (hasResolved) return;
      hasResolved = true;
      isPlaying = false;
      onCompleteRef.current(outcome);
    };

    // Keyboard handlers
    const handleKeyDown = (e: KeyboardEvent): void => {
      controller.keysDown.add(e.key);
    };
    const handleKeyUp = (e: KeyboardEvent): void => {
      controller.keysDown.delete(e.key);
    };
    const handleBlur = (): void => {
      controller.keysDown.clear();
      controller.isPointerDown = false;
      if (isPlaying && !hasResolved) {
        isPausedLocal = true;
        setIsPaused(true);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("keyup", handleKeyUp);
    window.addEventListener("blur", handleBlur);

    async function setup(): Promise<void> {
      await app.init({
        width: LOCK_CANVAS_WIDTH,
        height: LOCK_CANVAS_HEIGHT,
        background: 0x0a0c14,
        antialias: true,
      });

      isInitialized = true;
      if (destroyed) {
        app.destroy({ removeView: true }, { children: true });
        return;
      }

      mountEl.appendChild(app.canvas);

      // Pointer event listeners on the canvas
      const updatePointerAngle = (e: PointerEvent): void => {
        const rect = app.canvas.getBoundingClientRect();
        const scaleX = LOCK_CANVAS_WIDTH / rect.width;
        const scaleY = LOCK_CANVAS_HEIGHT / rect.height;
        const canvasX = (e.clientX - rect.left) * scaleX;
        const canvasY = (e.clientY - rect.top) * scaleY;
        controller.pointerAngleDeg = calculateAngleFromCenter(
          canvasX,
          canvasY,
          LOCK_CENTER_X,
          LOCK_CENTER_Y,
        );
      };

      const handlePointerDown = (e: PointerEvent): void => {
        controller.isPointerDown = true;
        updatePointerAngle(e);
      };

      const handlePointerMove = (e: PointerEvent): void => {
        if (controller.isPointerDown) {
          updatePointerAngle(e);
        }
      };

      const handlePointerUp = (): void => {
        controller.isPointerDown = false;
      };

      app.canvas.addEventListener("pointerdown", handlePointerDown);
      window.addEventListener("pointermove", handlePointerMove);
      window.addEventListener("pointerup", handlePointerUp);
      window.addEventListener("pointercancel", handlePointerUp);

      // Scene graphs
      const lockScene = createLockScene();
      const needleScene = createNeedleScene();
      const cylindersScene = createCylindersScene();

      app.stage.addChild(lockScene.container);
      app.stage.addChild(needleScene.container);
      app.stage.addChild(cylindersScene.container);

      // Initial draw
      lockScene.updateSweetSpot(
        simState.sweetSpotCenterDeg,
        preset.sweetSpotArcDeg,
        0,
        0,
      );
      needleScene.updateAngle(simState.pickAngleDeg, false);
      cylindersScene.updateCylinders(0, preset.cylinderCount);

      startRef.current = () => {
        isPlaying = true;
        isPausedLocal = false;
        setIsPaused(false);
      };

      pauseRef.current = () => {
        isPausedLocal = true;
        setIsPaused(true);
      };

      resumeRef.current = () => {
        isPausedLocal = false;
        setIsPaused(false);
      };

      // Game ticker
      app.ticker.add((ticker) => {
        if (!isPlaying || isPausedLocal || hasResolved) return;

        const deltaSec = ticker.deltaMS / 1000;
        elapsedMs += ticker.deltaMS;
        const remaining = Math.max(0, durationMs - elapsedMs);
        setTimeRemainingMs(remaining);

        // 1. Compute next pick angle
        const nextPickAngle = computeNextPickAngle(
          simState.pickAngleDeg,
          controller,
          deltaSec,
        );

        // 2. Step simulation
        simState = advanceSimulation(simState, deltaSec, preset, nextPickAngle);

        const inZone = isInSweetSpot(
          simState.pickAngleDeg,
          simState.sweetSpotCenterDeg,
          preset.sweetSpotArcDeg,
        );

        // Audio & Visual feedbacks
        if (simState.justClicked) {
          playCylinderClick();
          setCylindersClicked(simState.cylindersClicked);
        }

        if (simState.justBrokePick) {
          playPickBreakSfx();
          lockScene.flashBreak();
          needleScene.playBreakAnim();
          setPicksRemaining(simState.picksRemaining);
          setIsBroken(true);
          if (breakFlashTimer) window.clearTimeout(breakFlashTimer);
          breakFlashTimer = window.setTimeout(() => setIsBroken(false), 300);
        }

        if (inZone && elapsedMs - lastDwellTickTime >= DWELL_TICK_INTERVAL_MS) {
          lastDwellTickTime = elapsedMs;
          playDwellTick();
        }

        const dwellProgress = simState.dwellAccumulatedMs / preset.dwellMs;
        const tensionProgress =
          simState.tensionAccumulatedMs / preset.tensionWindowMs;

        // 3. Update scene rendering
        lockScene.updateSweetSpot(
          simState.sweetSpotCenterDeg,
          preset.sweetSpotArcDeg,
          dwellProgress,
          tensionProgress,
        );
        needleScene.updateAngle(simState.pickAngleDeg, inZone);
        cylindersScene.updateCylinders(
          simState.cylindersClicked,
          preset.cylinderCount,
        );

        // 4. Check terminal states
        if (simState.isUnlocked) {
          lockScene.flashUnlock();
          playWinStinger();
          resolve({ outcome_tag: "win", score: simState.picksRemaining });
        } else if (simState.isDefeated) {
          playLoseStinger();
          resolve({ outcome_tag: "lose", score: 0 });
        } else if (remaining <= 0) {
          playLoseStinger();
          resolve({ outcome_tag: "timeout", score: 0 });
        }
      });
    }

    void setup();

    return () => {
      destroyed = true;
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("keyup", handleKeyUp);
      window.removeEventListener("blur", handleBlur);
      if (breakFlashTimer) window.clearTimeout(breakFlashTimer);
      startRef.current = () => {};
      pauseRef.current = () => {};
      resumeRef.current = () => {};

      if (isInitialized) {
        app.destroy({ removeView: true }, { children: true });
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lockpickConfig.difficulty, lockpickConfig.picks]);

  const start = (): void => startRef.current();
  const pause = (): void => pauseRef.current();
  const resume = (): void => resumeRef.current();

  return {
    picksRemaining,
    initialPicks,
    cylindersClicked,
    totalCylinders: preset.cylinderCount,
    timeRemainingMs,
    durationMs,
    canvasContainerRef: containerRef,
    start,
    pause,
    resume,
    isBroken,
    isPaused,
  };
}
