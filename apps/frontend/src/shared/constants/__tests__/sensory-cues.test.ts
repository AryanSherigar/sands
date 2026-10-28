import { describe, expect, it } from "vitest";
import { SENSORY_CUE_IDS, isSensoryCueId } from "../sensory-cues";

describe("sensory cue ids", () => {
  it("has ten unique cues", () => {
    expect(new Set(SENSORY_CUE_IDS).size).toBe(10);
  });

  it("recognises known cues and rejects others", () => {
    expect(isSensoryCueId("phone_ring")).toBe(true);
    expect(isSensoryCueId("air_horn")).toBe(false);
  });
});
