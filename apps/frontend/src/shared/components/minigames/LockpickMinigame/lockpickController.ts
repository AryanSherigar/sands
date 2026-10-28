import { normalizeAngle } from "./lockpickPhysics";

export interface LockpickControllerState {
  keysDown: Set<string>;
  isPointerDown: boolean;
  pointerAngleDeg: number | null;
}

const KEYBOARD_TURN_SPEED_DEG_PER_SEC = 120;

export function calculateAngleFromCenter(
  x: number,
  y: number,
  centerX: number,
  centerY: number,
): number {
  const rad = Math.atan2(y - centerY, x - centerX);
  const deg = (rad * 180) / Math.PI;
  return normalizeAngle(deg);
}

export function createInitialControllerState(): LockpickControllerState {
  return {
    keysDown: new Set<string>(),
    isPointerDown: false,
    pointerAngleDeg: null,
  };
}

export function computeNextPickAngle(
  currentAngleDeg: number,
  controller: LockpickControllerState,
  deltaSec: number,
  keyboardSpeedDegPerSec: number = KEYBOARD_TURN_SPEED_DEG_PER_SEC,
): number {
  // If pointer is held down and dragging, mouse directly drives pick angle
  if (controller.isPointerDown && controller.pointerAngleDeg !== null) {
    return normalizeAngle(controller.pointerAngleDeg);
  }

  // Keyboard navigation
  let delta = 0;
  const left =
    controller.keysDown.has("ArrowLeft") ||
    controller.keysDown.has("a") ||
    controller.keysDown.has("A");
  const right =
    controller.keysDown.has("ArrowRight") ||
    controller.keysDown.has("d") ||
    controller.keysDown.has("D");

  if (left && !right) {
    delta = -keyboardSpeedDegPerSec * deltaSec;
  } else if (right && !left) {
    delta = keyboardSpeedDegPerSec * deltaSec;
  }

  return normalizeAngle(currentAngleDeg + delta);
}
