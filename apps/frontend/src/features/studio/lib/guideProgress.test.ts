import { describe, expect, it } from "vitest";
import type { ScenarioResponse } from "../types/scenario.types";
import { groupCards } from "./cardGroups";
import { getFirstUnfinishedStep, getStepStatus, isStepDone } from "./guideProgress";

const noCards = groupCards([]);

const scenario = (overrides: Partial<ScenarioResponse>): ScenarioResponse =>
  ({ title: "", logline: null, world_data: {}, status: "draft", ...overrides }) as ScenarioResponse;

describe("guideProgress", () => {
  it("marks Idea done only with both a one line idea and a name", () => {
    expect(isStepDone("idea", scenario({ logline: "A door", title: "" }), noCards)).toBe(false);
    expect(isStepDone("idea", scenario({ logline: "A door", title: "The Door" }), noCards)).toBe(true);
    expect(isStepDone("idea", null, noCards)).toBe(false);
  });

  it("marks Premise and World done from their written documents", () => {
    const written = scenario({
      world_data: {
        premiseDocument: { blocks: [{ kind: "text", text: "Mara finds a door" }] },
        worldLoreDocument: { blocks: [{ kind: "text", text: "A cold coast" }] },
      },
    });
    expect(isStepDone("premise", written, noCards)).toBe(true);
    expect(isStepDone("world", written, noCards)).toBe(true);
    expect(isStepDone("premise", scenario({}), noCards)).toBe(false);
  });

  it("treats a place card as World progress and the player card as Player progress", () => {
    const cards = groupCards([
      { entity_id: "a", entity_type: "location", canonical_name: "Lighthouse" },
      { entity_id: "b", entity_type: "character", canonical_name: "You", is_player: true },
    ] as never);
    expect(isStepDone("world", scenario({}), cards)).toBe(true);
    expect(isStepDone("player", scenario({}), cards)).toBe(true);
    expect(isStepDone("characters", scenario({}), cards)).toBe(false);
  });

  it("reports a done step as done even when it is the active one", () => {
    expect(getStepStatus(2, 2, true)).toBe("done");
    expect(getStepStatus(2, 2, false)).toBe("current");
    expect(getStepStatus(3, 2, false)).toBe("todo");
  });

  it("finds the first unfinished step", () => {
    expect(getFirstUnfinishedStep(null, noCards)).toBe(1);
    expect(
      getFirstUnfinishedStep(scenario({ logline: "A", title: "T" }), noCards),
    ).toBe(2);
  });
  describe("resume with Advanced mode", () => {
    const doneThroughOpening = scenario({
      logline: "A",
      title: "T",
      opening_scene: "The tide is out.",
      world_data: {
        premiseDocument: { blocks: [{ kind: "text", text: "Mara finds a door" }] },
        worldLoreDocument: { blocks: [{ kind: "text", text: "A cold coast" }] },
      },
    });
    const cards = groupCards([
      { entity_id: "a", entity_type: "character", canonical_name: "You", is_player: true },
      { entity_id: "b", entity_type: "character", canonical_name: "Tomas" },
    ] as never);

    it("lands on Finish at the right number in both modes", () => {
      expect(getFirstUnfinishedStep(doneThroughOpening, cards, false)).toBe(7);
      expect(getFirstUnfinishedStep(doneThroughOpening, cards, true)).toBe(12);
    });

    it("never resumes on an optional Advanced step", () => {
      expect(getFirstUnfinishedStep(scenario({ logline: "A", title: "T" }), noCards, true)).toBe(2);
    });

    it("does not treat Advanced steps as derived from the story row", () => {
      expect(isStepDone("endings", doneThroughOpening, cards)).toBe(false);
    });
  });
});
