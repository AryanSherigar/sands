import { describe, expect, it } from "vitest";
import { shouldIgnoreNarratorMood } from "../atmosphereSubscriber";

const withMoodMap = {
  meters: [],
  tier: {
    path: "tension_tier",
    hint: { kind: "tier" as const, label: "Tension", mood_map: { tense: "tension" } },
    options: ["uneasy", "tense"],
  },
};

describe("shouldIgnoreNarratorMood", () => {
  it("is true only with both tools on and a non-empty mood_map", () => {
    expect(
      shouldIgnoreNarratorMood({
        enabled_tools: ["status_hud", "atmosphere"],
        hud_hints: withMoodMap,
      }),
    ).toBe(true);
  });

  it.each([[["atmosphere"]], [["status_hud"]], [[]]])(
    "is false when the tools are %j",
    (tools) => {
      expect(
        shouldIgnoreNarratorMood({ enabled_tools: tools, hud_hints: withMoodMap }),
      ).toBe(false);
    },
  );

  it("is false without a mood_map or with an empty one", () => {
    const tools = ["status_hud", "atmosphere"];
    const noMap = {
      meters: [],
      tier: { ...withMoodMap.tier, hint: { kind: "tier" as const, label: "T" } },
    };
    const emptyMap = {
      meters: [],
      tier: {
        ...withMoodMap.tier,
        hint: { kind: "tier" as const, label: "T", mood_map: {} },
      },
    };

    expect(shouldIgnoreNarratorMood({ enabled_tools: tools, hud_hints: noMap })).toBe(false);
    expect(shouldIgnoreNarratorMood({ enabled_tools: tools, hud_hints: emptyMap })).toBe(false);
    expect(
      shouldIgnoreNarratorMood({ enabled_tools: tools, hud_hints: { meters: [] } }),
    ).toBe(false);
    expect(shouldIgnoreNarratorMood(null)).toBe(false);
  });
});
