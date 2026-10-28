import { describe, expect, it } from "vitest";
import { buildEntityFixture } from "../test/cardApiMock";
import { buildScenarioFixture } from "../test/studioApiMock";
import {
  buildSlotWrite,
  combineText,
  getFreeText,
  readSlotText,
  setFreeText,
} from "./scopedSlots";

const answer = { kind: "answer", question_id: "stakes", label: "Stakes", text: "Everything" } as const;

describe("free text of a lore document", () => {
  it("reads only the free text, leaving linked answers alone", () => {
    const document = { blocks: [{ kind: "text", text: "Hello" }, answer] } as const;
    expect(getFreeText({ blocks: [...document.blocks] })).toBe("Hello");
  });

  it("replaces free text and keeps linked answers", () => {
    const next = setFreeText({ blocks: [{ kind: "text", text: "Old" }, answer] }, "New");
    expect(next.blocks).toEqual([{ kind: "text", text: "New" }, answer]);
    expect(setFreeText({ blocks: [{ kind: "text", text: "Old" }] }, "  ").blocks).toEqual([]);
  });
});

describe("combineText", () => {
  it("replaces, or appends after existing text", () => {
    expect(combineText("old", "new", "replace")).toBe("new");
    expect(combineText("old", "new", "append")).toBe("old\n\nnew");
    expect(combineText("", "new", "append")).toBe("new");
  });
});

describe("slots", () => {
  it("reads and writes the title, clamped to 64 characters", () => {
    const source = { scenario: buildScenarioFixture({ title: "Old" }), entity: null };
    expect(readSlotText("title", source)).toBe("Old");
    const write = buildSlotWrite("title", source, "t".repeat(100));
    expect(write.scenarioPatch?.title).toHaveLength(64);
    expect(write.entityUpdate).toBeNull();
  });

  it("writes the premise into the premise document inside world data", () => {
    const source = { scenario: buildScenarioFixture(), entity: null };
    const write = buildSlotWrite("premise", source, "A war is coming.");
    expect(write.scenarioPatch?.worldData).toEqual({
      premiseDocument: { blocks: [{ kind: "text", text: "A war is coming." }] },
    });
  });

  it("writes the storytelling style to the persona document, not world data", () => {
    const source = { scenario: buildScenarioFixture(), entity: null };
    const write = buildSlotWrite("style", source, "Cozy");
    expect(write.scenarioPatch?.narrator_persona_document).toBeDefined();
    expect(write.scenarioPatch?.worldData).toBeUndefined();
  });

  it("writes a card's lore as an entity update only", () => {
    const entity = buildEntityFixture({ entity_id: "mara", canonical_name: "Mara" });
    const write = buildSlotWrite("card_lore", { scenario: null, entity }, "Keeper");
    expect(write.scenarioPatch).toBeNull();
    expect(write.entityUpdate?.lore_document?.blocks[0].text).toBe("Keeper");
  });
});
