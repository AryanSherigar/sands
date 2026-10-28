import { describe, expect, it } from "vitest";
import {
  buildDraftPayload,
  buildScenarioUpdate,
  hasFirstWord,
  mergeScenarioPatches,
  subtractScenarioPatch,
} from "../scenarioPatch";

describe("scenarioPatch", () => {
  it("treats blank and whitespace-only text as no first word", () => {
    expect(hasFirstWord({})).toBe(false);
    expect(hasFirstWord({ logline: "", title: "   " })).toBe(false);
    expect(hasFirstWord({ genre_tags: [], worldData: { premiseDocument: { blocks: [] } } })).toBe(false);
  });

  it("recognises real input anywhere in the patch", () => {
    expect(hasFirstWord({ logline: "A" })).toBe(true);
    expect(hasFirstWord({ worldData: { alwaysRemember: ["Never lie"] } })).toBe(true);
    expect(
      hasFirstWord({ worldData: { premiseDocument: { blocks: [{ kind: "text", text: "x" }] } } }),
    ).toBe(true);
  });

  it("merges world data keys instead of replacing them", () => {
    const merged = mergeScenarioPatches(
      { title: "A", worldData: { alwaysRemember: ["x"] } },
      { logline: "B", worldData: { worldLoreDocument: { blocks: [] } } },
    );
    expect(merged).toEqual({
      title: "A",
      logline: "B",
      worldData: { alwaysRemember: ["x"], worldLoreDocument: { blocks: [] } },
    });
  });

  it("writes world data on top of what the story already has", () => {
    const update = buildScenarioUpdate(
      { title: "T", worldData: { alwaysRemember: ["x"] } },
      { premiseDocument: { blocks: [] }, alwaysRemember: [] },
    );
    expect(update).toEqual({
      title: "T",
      world_data: { premiseDocument: { blocks: [] }, alwaysRemember: ["x"] },
    });
    expect(buildScenarioUpdate({ title: "T" }, { keep: true })).toEqual({ title: "T" });
  });

  it("builds a private newbie draft and clamps pasted text instead of rejecting it", () => {
    const payload = buildDraftPayload({
      logline: "x".repeat(400),
      title: "t".repeat(100),
      worldData: { alwaysRemember: [] },
    });
    expect(payload.mode).toBe("newbie");
    expect(payload.visibility).toBe("private");
    expect(payload.complexity_tier).toBe("newbie");
    expect(payload.logline).toHaveLength(150);
    expect(payload.title).toHaveLength(64);
    expect(payload.world_data).toEqual({ alwaysRemember: [] });
  });

  it("starts every draft with the Name setup field", () => {
    const payload = buildDraftPayload({ logline: "A door" });
    expect(payload.setup_schema).toEqual([
      expect.objectContaining({ label: "Name", is_character_name: true }),
    ]);
  });

  it("allows a draft with no title yet", () => {
    expect(buildDraftPayload({ logline: "A door" }).title).toBe("");
  });

  it("subtracts only the fields that were written, including world data keys", () => {
    const remaining = subtractScenarioPatch(
      { title: "A", logline: "B", worldData: { premiseDocument: 1, alwaysRemember: 2 } },
      { logline: "C", worldData: { premiseDocument: 3 } },
    );
    expect(remaining).toEqual({ title: "A", worldData: { alwaysRemember: 2 } });
    expect(subtractScenarioPatch({ title: "A", worldData: { x: 1 } }, { title: "B", worldData: { x: 2 } })).toEqual({});
  });
});
