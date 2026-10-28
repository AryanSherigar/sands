import { describe, expect, it } from "vitest";
import {
  advanceSimulation,
  angleDifference,
  createInitialSimState,
  isInSweetSpot,
  normalizeAngle,
} from "../lockpickPhysics";
import { LOCKPICK_DIFFICULTY_PRESETS } from "../lockpickPresets";

describe("lockpickPhysics", () => {
  describe("angle math", () => {
    it("normalizes angles to [0, 360)", () => {
      expect(normalizeAngle(0)).toBe(0);
      expect(normalizeAngle(360)).toBe(0);
      expect(normalizeAngle(720)).toBe(0);
      expect(normalizeAngle(-90)).toBe(270);
      expect(normalizeAngle(450)).toBe(90);
    });

    it("computes shortest distance across 0/360 boundary", () => {
      expect(angleDifference(10, 20)).toBe(10);
      expect(angleDifference(350, 10)).toBe(20);
      expect(angleDifference(10, 350)).toBe(20);
      expect(angleDifference(0, 180)).toBe(180);
      expect(angleDifference(5, 185)).toBe(180);
    });

    it("checks if pick is within sweet-spot arc", () => {
      // 30 degree arc centered at 90 => bounds are [75, 105]
      expect(isInSweetSpot(90, 90, 30)).toBe(true);
      expect(isInSweetSpot(75, 90, 30)).toBe(true);
      expect(isInSweetSpot(105, 90, 30)).toBe(true);
      expect(isInSweetSpot(74, 90, 30)).toBe(false);
      expect(isInSweetSpot(106, 90, 30)).toBe(false);
    });

    it("checks sweet spot wrapping around 0 degrees", () => {
      // 40 degree arc centered at 0 => [340, 360) and [0, 20]
      expect(isInSweetSpot(0, 0, 40)).toBe(true);
      expect(isInSweetSpot(15, 0, 40)).toBe(true);
      expect(isInSweetSpot(350, 0, 40)).toBe(true);
      expect(isInSweetSpot(25, 0, 40)).toBe(false);
      expect(isInSweetSpot(335, 0, 40)).toBe(false);
    });
  });

  describe("advanceSimulation", () => {
    const preset = LOCKPICK_DIFFICULTY_PRESETS[1]; // dwell: 500ms, tension: 2500ms, cylinders: 2

    it("clicks cylinder when dwelling in sweet spot for dwellMs", () => {
      let state = createInitialSimState(3, 90, 90);

      // Advance by 0.3s (300ms) - not enough to click yet
      state = advanceSimulation(state, 0.3, preset, 90);
      expect(state.cylindersClicked).toBe(0);
      expect(state.justClicked).toBe(false);
      expect(state.dwellAccumulatedMs).toBeCloseTo(300, -1);

      // Advance another 0.3s (600ms total > 500ms dwell)
      state = advanceSimulation(state, 0.3, preset, 90);
      expect(state.cylindersClicked).toBe(1);
      expect(state.justClicked).toBe(true);
      expect(state.dwellAccumulatedMs).toBe(0);
    });

    it("unlocks when all cylinders are clicked", () => {
      let state = createInitialSimState(3, 90, 90);

      // Cylinder 1
      state = advanceSimulation(state, 0.6, preset, 90);
      expect(state.cylindersClicked).toBe(1);
      expect(state.isUnlocked).toBe(false);

      // Cylinder 2 (preset 1 has 2 cylinders)
      state = advanceSimulation(state, 0.6, preset, 90);
      expect(state.cylindersClicked).toBe(2);
      expect(state.isUnlocked).toBe(true);
      expect(state.isDefeated).toBe(false);
    });

    it("breaks pick when holding outside sweet spot for tensionWindowMs", () => {
      let state = createInitialSimState(3, 180, 90); // 180 is far from 90

      // Advance by 2.0s (< 2500ms)
      state = advanceSimulation(state, 2.0, preset, 180);
      expect(state.picksRemaining).toBe(3);
      expect(state.justBrokePick).toBe(false);

      // Advance another 0.6s (2.6s total > 2500ms)
      state = advanceSimulation(state, 0.6, preset, 180);
      expect(state.picksRemaining).toBe(2);
      expect(state.justBrokePick).toBe(true);
    });

    it("results in defeat when all picks are broken", () => {
      let state = createInitialSimState(1, 180, 90); // only 1 pick remaining

      state = advanceSimulation(state, 2.6, preset, 180);
      expect(state.picksRemaining).toBe(0);
      expect(state.isDefeated).toBe(true);
      expect(state.isUnlocked).toBe(false);
    });
  });
});
