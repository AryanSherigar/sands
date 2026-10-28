import { describe, expect, it } from "vitest";
import { computeAdjacency } from "./computeAdjacency";
import { extractArcs } from "./extractArcs";
import { traceLabelMap } from "./traceLabelMap";
import { makeLabelMapFromRows } from "./testImages";
import type { TraceOptions } from "@/shared/types/strategy-map.types";

const OPTIONS: TraceOptions = { source: "manual", imageUrl: null };

function scaleRows(rows: string[], factor: number): string[] {
  return rows.flatMap((row) => {
    const wide = [...row].map((char) => char.repeat(factor)).join("");
    return Array.from({ length: factor }, () => wide);
  });
}

function trace(rows: string[], options: TraceOptions = OPTIONS) {
  return traceLabelMap(makeLabelMapFromRows(scaleRows(rows, 10)), {}, options);
}

describe("computeAdjacency", () => {
  it("ignores corner-only contact and short borders", () => {
    const map = makeLabelMapFromRows(scaleRows(["ab", "cd"], 10));
    const adjacency = computeAdjacency(extractArcs(map));
    expect(adjacency.get(1)).toEqual(new Set([2, 3]));
    expect(adjacency.get(4)).toEqual(new Set([2, 3]));
  });

  it("needs a minimum shared border", () => {
    const map = makeLabelMapFromRows(["aab", "aab"]);
    expect(computeAdjacency(extractArcs(map)).get(1)?.size ?? 0).toBe(0);
  });
});

describe("traceLabelMap", () => {
  it("builds symmetric neighbours and copies the map size", () => {
    const { document } = trace(["ab", "cd"]);
    expect(document.width).toBe(20);
    expect(document.height).toBe(20);
    const byId = new Map(document.regions.map((region) => [region.id, region]));
    expect(byId.get("region_01")?.neighbor_ids).toEqual(["region_02", "region_03"]);
    for (const region of document.regions) {
      for (const neighbor of region.neighbor_ids) {
        expect(byId.get(neighbor)?.neighbor_ids).toContain(region.id);
      }
    }
  });

  it("keeps a two-piece colour as one region and flags it", () => {
    const { document, problems } = trace(["aba", "aba"]);
    expect(document.regions).toHaveLength(2);
    const outline = document.regions[0].outline;
    expect(outline.split("M").length - 1).toBe(2);
    expect(problems.map((problem) => problem.kind)).toContain("split_color");
  });

  it("flags a region whose outline cannot fit the limit", () => {
    const { problems } = trace(["ab"], { ...OPTIONS, maxOutlineChars: 10 });
    expect(problems.filter((p) => p.kind === "too_detailed").length).toBeGreaterThan(0);
  });

  it("never emits an empty outline when tolerance grows", () => {
    const { document } = trace(["ab"], { ...OPTIONS, maxOutlineChars: 10 });
    expect(document.regions.every((region) => region.outline.length > 0)).toBe(true);
  });

  it("reports unassigned pixels instead of tracing them as a region", () => {
    const { document, problems } = trace(["a.", "a."]);
    expect(document.regions).toHaveLength(1);
    expect(problems.map((problem) => problem.kind)).toContain("unassigned_pixels");
  });

  it("is deterministic", () => {
    expect(JSON.stringify(trace(["abc", "dbc"]))).toBe(
      JSON.stringify(trace(["abc", "dbc"])),
    );
  });

  it("uses supplied names and terrain, placeholders otherwise", () => {
    const map = makeLabelMapFromRows(scaleRows(["ab"], 10));
    const meta = { region_01: { name: "Ashford", terrain: "hills" as const } };
    const { document } = traceLabelMap(map, meta, OPTIONS);
    expect(document.regions[0]).toMatchObject({ name: "Ashford", terrain: "hills" });
    expect(document.regions[1]).toMatchObject({ name: "Region 2", terrain: "plain" });
  });
});
