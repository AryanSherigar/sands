import { LockpickPreset } from "./lockpickPresets";

export interface LockpickSimState {
  pickAngleDeg: number;
  sweetSpotCenterDeg: number;
  sweetSpotDirection: 1 | -1;
  dwellAccumulatedMs: number;
  tensionAccumulatedMs: number;
  cylindersClicked: number;
  picksRemaining: number;
  isUnlocked: boolean;
  isDefeated: boolean;
  justClicked: boolean;
  justBrokePick: boolean;
}

const MIN_SWEET_SPOT_BOUND = 45;
const MAX_SWEET_SPOT_BOUND = 315;

export function normalizeAngle(deg: number): number {
  let normalized = deg % 360;
  if (normalized < 0) normalized += 360;
  return normalized;
}

export function angleDifference(degA: number, degB: number): number {
  const diff = Math.abs(normalizeAngle(degA) - normalizeAngle(degB));
  return diff > 180 ? 360 - diff : diff;
}

export function isInSweetSpot(
  pickAngleDeg: number,
  sweetSpotCenterDeg: number,
  arcWidthDeg: number,
): boolean {
  return angleDifference(pickAngleDeg, sweetSpotCenterDeg) <= arcWidthDeg / 2;
}

export function createInitialSimState(
  initialPicks: number,
  initialPickAngle: number = 180,
  initialSweetSpot: number = 90,
): LockpickSimState {
  return {
    pickAngleDeg: normalizeAngle(initialPickAngle),
    sweetSpotCenterDeg: normalizeAngle(initialSweetSpot),
    sweetSpotDirection: 1,
    dwellAccumulatedMs: 0,
    tensionAccumulatedMs: 0,
    cylindersClicked: 0,
    picksRemaining: initialPicks,
    isUnlocked: false,
    isDefeated: false,
    justClicked: false,
    justBrokePick: false,
  };
}

export function advanceSimulation(
  state: LockpickSimState,
  deltaSec: number,
  preset: LockpickPreset,
  nextPickAngleDeg: number,
): LockpickSimState {
  if (state.isUnlocked || state.isDefeated) {
    return { ...state, justClicked: false, justBrokePick: false };
  }

  // 1. Advance sweet spot oscillation
  let nextSweetSpot =
    state.sweetSpotCenterDeg +
    preset.oscillationSpeedDegPerSec * deltaSec * state.sweetSpotDirection;
  let nextDirection = state.sweetSpotDirection;

  if (nextSweetSpot >= MAX_SWEET_SPOT_BOUND) {
    nextSweetSpot = MAX_SWEET_SPOT_BOUND;
    nextDirection = -1;
  } else if (nextSweetSpot <= MIN_SWEET_SPOT_BOUND) {
    nextSweetSpot = MIN_SWEET_SPOT_BOUND;
    nextDirection = 1;
  }

  const normalizedPickAngle = normalizeAngle(nextPickAngleDeg);
  const inZone = isInSweetSpot(
    normalizedPickAngle,
    nextSweetSpot,
    preset.sweetSpotArcDeg,
  );

  let dwell = state.dwellAccumulatedMs;
  let tension = state.tensionAccumulatedMs;
  let cylinders = state.cylindersClicked;
  let picks = state.picksRemaining;
  let justClicked = false;
  let justBroke = false;

  if (inZone) {
    dwell += deltaSec * 1000;
    tension = Math.max(0, tension - deltaSec * 2000);

    if (dwell >= preset.dwellMs) {
      cylinders += 1;
      dwell = 0;
      justClicked = true;
    }
  } else {
    dwell = Math.max(0, dwell - deltaSec * 1500);
    tension += deltaSec * 1000;

    if (tension >= preset.tensionWindowMs) {
      picks -= 1;
      tension = 0;
      justBroke = true;
    }
  }

  const isUnlocked = cylinders >= preset.cylinderCount;
  const isDefeated = picks <= 0;

  return {
    pickAngleDeg: normalizedPickAngle,
    sweetSpotCenterDeg: nextSweetSpot,
    sweetSpotDirection: nextDirection,
    dwellAccumulatedMs: dwell,
    tensionAccumulatedMs: tension,
    cylindersClicked: cylinders,
    picksRemaining: picks,
    isUnlocked,
    isDefeated,
    justClicked,
    justBrokePick: justBroke,
  };
}
