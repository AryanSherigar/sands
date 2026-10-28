import { describe, expect, it } from "vitest";
import {
  clampGuideStep,
  getGuideStepCount,
  getGuideSteps,
  isAdvancedStepId,
  remapGuideStep,
} from "./guideStepsFor";

describe("getGuideSteps", () => {
  it("keeps the seven base steps when Advanced is off", () => {
    const steps = getGuideSteps(false);
    expect(steps.map((step) => step.id)).toEqual([
      "idea",
      "premise",
      "player",
      "characters",
      "world",
      "opening",
      "finish",
    ]);
    expect(steps.map((step) => step.number)).toEqual([1, 2, 3, 4, 5, 6, 7]);
    expect(getGuideStepCount(false)).toBe(7);
  });

  it("inserts the five Advanced steps between Opening and Finish and renumbers", () => {
    const steps = getGuideSteps(true);
    expect(steps.slice(5).map((step) => step.id)).toEqual([
      "opening",
      "endings",
      "tracked_values",
      "rules",
      "hard_limits",
      "extras",
      "finish",
    ]);
    expect(steps.map((step) => step.number)).toEqual([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]);
    expect(steps.at(-1)?.name).toBe("Finish");
    expect(getGuideStepCount(true)).toBe(12);
  });

  it("uses the plain-word headers", () => {
    const headers = Object.fromEntries(getGuideSteps(true).map((step) => [step.id, step.header]));
    expect(headers.endings).toBe("How can the story end?");
    expect(headers.tracked_values).toBe("What matters along the way?");
    expect(headers.rules).toBe("What happens when…?");
    expect(headers.hard_limits).toBe("What can never happen?");
    expect(headers.extras).toBe("Want to add more?");
  });
});

describe("isAdvancedStepId", () => {
  it("is true only for the five Advanced steps", () => {
    expect(isAdvancedStepId("endings")).toBe(true);
    expect(isAdvancedStepId("extras")).toBe(true);
    expect(isAdvancedStepId("finish")).toBe(false);
  });
});

describe("remapGuideStep", () => {
  it("keeps base steps where they are", () => {
    expect(remapGuideStep(3, false, true)).toBe(3);
    expect(remapGuideStep(6, true, false)).toBe(6);
  });

  it("moves Finish with the mode", () => {
    expect(remapGuideStep(7, false, true)).toBe(12);
    expect(remapGuideStep(12, true, false)).toBe(7);
  });

  it("falls back to Opening when the Advanced step disappears", () => {
    expect(remapGuideStep(9, true, false)).toBe(6);
  });

  it("clamps numbers outside the list", () => {
    expect(remapGuideStep(99, true, false)).toBe(7);
  });
});

describe("clampGuideStep", () => {
  it("keeps a valid step", () => {
    expect(clampGuideStep(4, false)).toBe(4);
    expect(clampGuideStep(9, true)).toBe(9);
  });

  it("falls back to Opening when a remembered Advanced step is out of range", () => {
    expect(clampGuideStep(9, false)).toBe(6);
  });

  it("never goes below the first step", () => {
    expect(clampGuideStep(0, true)).toBe(1);
  });
});
