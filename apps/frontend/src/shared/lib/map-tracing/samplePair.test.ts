import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { PNG } from "pngjs";
import { describe, expect, it } from "vitest";
import { buildLabelMap } from "./buildLabelMap";
import { checkMap, isBlockingProblem } from "./mapChecks";
import { traceLabelMap } from "./traceLabelMap";
import type { PixelImage } from "@/shared/types/strategy-map.types";

const MAX_TRACE_MS = 3000;
const EXPECTED_MIN_REGIONS = 9;
const EXPECTED_MAX_REGIONS = 11;

function loadSample(): PixelImage {
  const png = PNG.sync.read(readFileSync(resolve(process.cwd(), "src/test/fixtures/strategy-map/sample-regions.png")));
  return { width: png.width, height: png.height, data: new Uint8ClampedArray(png.data) };
}

function subpathCount(outline: string): number {
  return outline.split("M").length - 1;
}

describe("sample map pair (AI-generated region colour image)", () => {
  const startedAt = performance.now();
  const image = loadSample();
  const { labelMap } = buildLabelMap(image);
  const { document, problems, pixelCounts } = traceLabelMap(
    labelMap,
    {},
    { source: "color_image", imageUrl: null },
  );
  const elapsed = performance.now() - startedAt;

  it("finds about ten regions out of ~32,000 noisy colours", () => {
    expect(document.regions.length).toBeGreaterThanOrEqual(EXPECTED_MIN_REGIONS);
    expect(document.regions.length).toBeLessThanOrEqual(EXPECTED_MAX_REGIONS);
  });

  it("keeps the two orange pieces as one two-subpath region", () => {
    expect(document.regions.some((region) => subpathCount(region.outline) >= 2)).toBe(true);
  });

  it("finds the white enclave touching exactly one neighbour", () => {
    expect(document.regions.some((region) => region.neighbor_ids.length === 1)).toBe(true);
  });

  it("has symmetric neighbours and only naming problems left to fix", () => {
    const byId = new Map(document.regions.map((region) => [region.id, region]));
    for (const region of document.regions) {
      for (const neighbor of region.neighbor_ids) {
        expect(byId.get(neighbor)?.neighbor_ids).toContain(region.id);
      }
    }
    const blocking = [...problems, ...checkMap(document, {}, pixelCounts)]
      .filter(isBlockingProblem)
      .map((problem) => problem.kind);
    expect(new Set(blocking)).toEqual(new Set(["unnamed", "no_terrain"]));
  });

  it("traces within the time budget", () => {
    expect(elapsed).toBeLessThan(MAX_TRACE_MS);
  });
});
