import { describe, expect, it } from "vitest";
import { SCOPED_TAB_TEXT_MAX_CHARS } from "../constants/scopedChat";
import { buildCardTabId } from "./studioTabs";
import { buildScenarioFixture } from "../test/studioApiMock";
import { buildEntityFixture } from "../test/cardApiMock";
import { groupCards } from "./cardGroups";
import {
  buildCardTabText,
  buildGuideTabText,
  buildScopedTabLabel,
  clampTabText,
  getSlotForTarget,
  resolveScopedTab,
  toScopedRequestContext,
} from "./scopedChat";

describe("resolveScopedTab", () => {
  it("maps the Guide to its current step, or to the whole editor", () => {
    expect(resolveScopedTab("guide", 5, "steps")).toEqual({ kind: "guide", stepId: "world" });
    expect(resolveScopedTab("guide", 5, "editor")).toEqual({ kind: "guide", stepId: null });
  });

  it("maps card, playtest and no tab", () => {
    expect(resolveScopedTab(buildCardTabId("mara"), 1, "steps")).toEqual({
      kind: "card",
      entityId: "mara",
    });
    expect(resolveScopedTab("playtest", 1, "steps")).toEqual({ kind: "playtest" });
    expect(resolveScopedTab(null, 1, "steps")).toEqual({ kind: "none" });
  });
});

describe("getSlotForTarget", () => {
  it("lets each Guide step write only its own fields", () => {
    const idea = resolveScopedTab("guide", 1, "steps");
    expect(getSlotForTarget(idea, "title")).toBe("title");
    expect(getSlotForTarget(idea, "lore")).toBeNull();
    const world = resolveScopedTab("guide", 5, "steps");
    expect(getSlotForTarget(world, "lore")).toBe("world_lore");
    expect(getSlotForTarget(world, "title")).toBeNull();
  });

  it("lets a card tab write its lore and nothing else", () => {
    const card = resolveScopedTab(buildCardTabId("mara"), 1, "steps");
    expect(getSlotForTarget(card, "story_card")).toBe("card_lore");
    expect(getSlotForTarget(card, "logline")).toBeNull();
  });

  it("writes nothing from the Playtest tab", () => {
    expect(getSlotForTarget({ kind: "playtest" }, "title")).toBeNull();
  });
});

describe("tab text", () => {
  it("clamps long tab text to the named limit", () => {
    const clamped = clampTabText("x".repeat(SCOPED_TAB_TEXT_MAX_CHARS + 500));
    expect(clamped).toHaveLength(SCOPED_TAB_TEXT_MAX_CHARS);
    expect(clampTabText("short")).toBe("short");
  });

  it("describes the current Guide step only", () => {
    const scenario = buildScenarioFixture({ title: "The Door", logline: "A door in the sea" });
    const text = buildGuideTabText("idea", scenario, groupCards([]));
    expect(text).toContain("Name: The Door");
    expect(text).toContain("One line idea: A door in the sea");
    expect(buildGuideTabText("premise", scenario, groupCards([]))).toBe("");
  });

  it("describes a card by name, triggers and lore", () => {
    const mara = buildEntityFixture({
      entity_id: "mara",
      canonical_name: "Mara",
      lore_document: { blocks: [{ kind: "text", text: "Keeps the light." }] },
    });
    const text = buildCardTabText(mara);
    expect(text).toContain("Name: Mara");
    expect(text).toContain("Keeps the light.");
  });

  it("names the Guide step in the label", () => {
    expect(buildScopedTabLabel({ kind: "guide", stepId: "world" }, "Guide")).toBe("Guide · World");
    expect(buildScopedTabLabel({ kind: "guide", stepId: null }, "Guide")).toBe("Guide");
  });

  it("builds the snake_case request context with the clamp applied", () => {
    const payload = toScopedRequestContext({
      oneLineIdea: "idea",
      tabKind: "guide",
      tabLabel: "Guide",
      tabText: "y".repeat(SCOPED_TAB_TEXT_MAX_CHARS + 1),
    });
    expect(payload.one_line_idea).toBe("idea");
    expect(payload.tab_text).toHaveLength(SCOPED_TAB_TEXT_MAX_CHARS);
  });
});
