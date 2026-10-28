import { describe, expect, it } from "vitest";
import {
  LOCKPICK_DIFFICULTY_PRESETS,
  LOCKPICK_MAX_DIFFICULTY,
  LOCKPICK_MIN_DIFFICULTY,
  getLockpickPreset,
} from "../lockpickPresets";

describe("lockpickPresets", () => {
  it("has presets for all difficulties 1 through 5", () => {
    for (let d = LOCKPICK_MIN_DIFFICULTY; d <= LOCKPICK_MAX_DIFFICULTY; d++) {
      expect(LOCKPICK_DIFFICULTY_PRESETS[d]).toBeDefined();
    }
  });

  it("enforces monotonic difficulty progression from 1 to 5", () => {
    for (let d = 1; d < 5; d++) {
      const current = LOCKPICK_DIFFICULTY_PRESETS[d];
      const next = LOCKPICK_DIFFICULTY_PRESETS[d + 1];

      // sweetSpotArcDeg must be strictly decreasing (narrower = harder)
      expect(next.sweetSpotArcDeg).toBeLessThan(current.sweetSpotArcDeg);

      // oscillationSpeedDegPerSec must be strictly increasing (faster = harder)
      expect(next.oscillationSpeedDegPerSec).toBeGreaterThan(
        current.oscillationSpeedDegPerSec,
      );

      // cylinderCount must be non-decreasing
      expect(next.cylinderCount).toBeGreaterThanOrEqual(current.cylinderCount);

      // tensionWindowMs must be strictly decreasing (shorter window before break)
      expect(next.tensionWindowMs).toBeLessThan(current.tensionWindowMs);
    }
  });

  it("clamps invalid difficulty numbers safely", () => {
    expect(getLockpickPreset(0)).toEqual(LOCKPICK_DIFFICULTY_PRESETS[1]);
    expect(getLockpickPreset(99)).toEqual(LOCKPICK_DIFFICULTY_PRESETS[5]);
    expect(getLockpickPreset(3.2)).toEqual(LOCKPICK_DIFFICULTY_PRESETS[3]);
  });
});
