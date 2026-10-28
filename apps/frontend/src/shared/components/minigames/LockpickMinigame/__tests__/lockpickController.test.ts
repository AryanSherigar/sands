import { describe, expect, it } from "vitest";
import {
  calculateAngleFromCenter,
  computeNextPickAngle,
  createInitialControllerState,
} from "../lockpickController";

describe("lockpickController", () => {
  it("calculates angle from center accurately", () => {
    // (100, 0) relative to (0, 0) is right -> 0 deg
    expect(calculateAngleFromCenter(100, 0, 0, 0)).toBe(0);

    // (0, 100) relative to (0, 0) is down -> 90 deg
    expect(calculateAngleFromCenter(0, 100, 0, 0)).toBe(90);

    // (-100, 0) relative to (0, 0) is left -> 180 deg
    expect(calculateAngleFromCenter(-100, 0, 0, 0)).toBe(180);

    // (0, -100) relative to (0, 0) is up -> 270 deg
    expect(calculateAngleFromCenter(0, -100, 0, 0)).toBe(270);
  });

  it("rotates pick with keyboard keys", () => {
    const state = createInitialControllerState();
    state.keysDown.add("ArrowRight");

    // 120 deg/s * 0.5s = +60 deg
    const next = computeNextPickAngle(100, state, 0.5, 120);
    expect(next).toBe(160);

    state.keysDown.clear();
    state.keysDown.add("a"); // rotate left
    const nextLeft = computeNextPickAngle(100, state, 0.5, 120);
    expect(nextLeft).toBe(40);
  });

  it("prioritizes pointer drag when pointer is down", () => {
    const state = createInitialControllerState();
    state.keysDown.add("ArrowRight"); // keyboard is also active
    state.isPointerDown = true;
    state.pointerAngleDeg = 215; // mouse is pointing to 215 deg

    const next = computeNextPickAngle(100, state, 0.5, 120);
    expect(next).toBe(215);
  });
});
