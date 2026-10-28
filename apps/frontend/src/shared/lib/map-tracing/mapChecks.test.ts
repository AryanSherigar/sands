import { describe, expect, it } from "vitest";
import { checkMap, isBlockingProblem, isMapFinishable } from "./mapChecks";
import type {
  MapDocument,
  MapRegion,
  RegionMeta,
} from "@/shared/types/strategy-map.types";

function region(id: string, neighbors: string[]): MapRegion {
  return {
    id,
    name: id,
    terrain: "plain",
    outline: "M0 0 L1 0 L1 1 Z",
    label_point: { x: 0, y: 0 },
    neighbor_ids: neighbors,
    source_color: null,
    source_ref: null,
  };
}

function documentOf(regions: MapRegion[]): MapDocument {
  return {
    schema_version: 1,
    source: "manual",
    width: 10,
    height: 10,
    image_url: null,
    regions,
    roads: [],
  };
}

function fullMeta(ids: string[]): Record<string, RegionMeta> {
  return Object.fromEntries(ids.map((id) => [id, { name: id, terrain: "plain" as const }]));
}

const kinds = (problems: { kind: string }[]): string[] => problems.map((p) => p.kind);

describe("checkMap", () => {
  const pair = documentOf([region("region_01", ["region_02"]), region("region_02", ["region_01"])]);

  it("flags unnamed regions and regions without terrain", () => {
    const meta = { region_01: { name: "  ", terrain: null }, region_02: { name: "B", terrain: "hills" as const } };
    const problems = checkMap(pair, meta);
    expect(problems).toContainEqual(expect.objectContaining({ regionId: "region_01", kind: "unnamed" }));
    expect(problems).toContainEqual(expect.objectContaining({ regionId: "region_01", kind: "no_terrain" }));
    expect(kinds(problems)).not.toContain("disconnected");
  });

  it("flags a one-way neighbour link", () => {
    const oneWay = documentOf([region("region_01", ["region_02"]), region("region_02", [])]);
    expect(kinds(checkMap(oneWay, fullMeta(["region_01", "region_02"])))).toContain("one_way_link");
  });

  it("flags a region group cut off from the rest", () => {
    const split = documentOf([
      region("region_01", ["region_02"]),
      region("region_02", ["region_01"]),
      region("region_03", []),
    ]);
    const problems = checkMap(split, fullMeta(["region_01", "region_02", "region_03"]));
    expect(problems).toContainEqual(expect.objectContaining({ regionId: "region_03", kind: "disconnected" }));
  });

  it("warns about tiny regions using pixel counts and about small maps", () => {
    const problems = checkMap(pair, fullMeta(["region_01", "region_02"]), { region_01: 10, region_02: 5000 });
    expect(problems).toContainEqual(expect.objectContaining({ regionId: "region_01", kind: "tiny" }));
    expect(kinds(problems)).toContain("few_regions");
  });
});

describe("isMapFinishable", () => {
  it("is false when any blocking problem exists", () => {
    expect(isMapFinishable([{ regionId: "a", kind: "unnamed", detail: "" }])).toBe(false);
    expect(isMapFinishable([{ regionId: null, kind: "unassigned_pixels", detail: "" }])).toBe(false);
  });

  it("is true with only warnings", () => {
    expect(
      isMapFinishable([
        { regionId: "a", kind: "tiny", detail: "" },
        { regionId: null, kind: "few_regions", detail: "" },
        { regionId: "a", kind: "split_color", detail: "" },
      ]),
    ).toBe(true);
  });
});

describe("isBlockingProblem", () => {
  it("treats only warnings as non-blocking", () => {
    expect(isBlockingProblem({ regionId: null, kind: "too_detailed", detail: "" })).toBe(true);
    expect(isBlockingProblem({ regionId: null, kind: "few_regions", detail: "" })).toBe(false);
  });
});
