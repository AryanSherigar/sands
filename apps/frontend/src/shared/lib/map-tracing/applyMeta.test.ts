import { describe, expect, it } from "vitest";
import { applyMetaToDocument } from "./applyMeta";
import { makeLabelMapFromRows } from "./testImages";
import { traceLabelMap } from "./traceLabelMap";

describe("applyMetaToDocument", () => {
  const rows = ["aaaaab", "aaaaab"];
  const { document } = traceLabelMap(makeLabelMapFromRows(rows), {}, { source: "manual", imageUrl: null });

  it("writes names and terrain without touching geometry", () => {
    const result = applyMetaToDocument(document, { region_01: { name: " Ashford ", terrain: "hills" } });
    expect(result.regions[0]).toMatchObject({ name: "Ashford", terrain: "hills" });
    expect(result.regions[0].outline).toBe(document.regions[0].outline);
  });

  it("keeps placeholders for regions without meta", () => {
    const result = applyMetaToDocument(document, {});
    expect(result.regions[1].name).toBe(document.regions[1].name);
    expect(result.regions[1].terrain).toBe("plain");
  });
});
