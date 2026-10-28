// Difficulty presets for Lockpick minigame.
// The creator-facing knob is a single 1-5 slider (lockpick_config.difficulty) —
// every other tuning value is derived from this table.

export interface LockpickPreset {
  sweetSpotArcDeg: number;
  oscillationSpeedDegPerSec: number;
  cylinderCount: number;
  dwellMs: number;
  tensionWindowMs: number;
}

// Difficulty 1 (gentlest) through 5 (hardest).
// Monotonically harder:
// - sweetSpotArcDeg strictly decreasing
// - oscillationSpeedDegPerSec strictly increasing
// - cylinderCount non-decreasing
// - tensionWindowMs strictly decreasing
export const LOCKPICK_DIFFICULTY_PRESETS: Record<number, LockpickPreset> = {
  1: {
    sweetSpotArcDeg: 60,
    oscillationSpeedDegPerSec: 20,
    cylinderCount: 2,
    dwellMs: 500,
    tensionWindowMs: 2500,
  },
  2: {
    sweetSpotArcDeg: 45,
    oscillationSpeedDegPerSec: 30,
    cylinderCount: 3,
    dwellMs: 550,
    tensionWindowMs: 2000,
  },
  3: {
    sweetSpotArcDeg: 30,
    oscillationSpeedDegPerSec: 45,
    cylinderCount: 3,
    dwellMs: 600,
    tensionWindowMs: 1500,
  },
  4: {
    sweetSpotArcDeg: 20,
    oscillationSpeedDegPerSec: 65,
    cylinderCount: 4,
    dwellMs: 650,
    tensionWindowMs: 1200,
  },
  5: {
    sweetSpotArcDeg: 12,
    oscillationSpeedDegPerSec: 90,
    cylinderCount: 5,
    dwellMs: 700,
    tensionWindowMs: 900,
  },
};

export const LOCKPICK_MIN_DIFFICULTY = 1;
export const LOCKPICK_MAX_DIFFICULTY = 5;
const LOCKPICK_DEFAULT_DIFFICULTY = 3;

export const LOCK_CANVAS_WIDTH = 640;
export const LOCK_CANVAS_HEIGHT = 480;
export const LOCK_CENTER_X = LOCK_CANVAS_WIDTH / 2;
export const LOCK_CENTER_Y = LOCK_CANVAS_HEIGHT / 2;
export const LOCK_OUTER_RADIUS = 160;
export const LOCK_INNER_RADIUS = 120;
export const PICK_NEEDLE_LENGTH = 150;
export const KEYHOLE_RADIUS = 30;

export function getLockpickPreset(difficulty: number): LockpickPreset {
  const clamped = Math.min(
    LOCKPICK_MAX_DIFFICULTY,
    Math.max(LOCKPICK_MIN_DIFFICULTY, Math.round(difficulty)),
  );
  return (
    LOCKPICK_DIFFICULTY_PRESETS[clamped] ??
    LOCKPICK_DIFFICULTY_PRESETS[LOCKPICK_DEFAULT_DIFFICULTY]
  );
}
