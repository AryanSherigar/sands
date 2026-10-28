import { describe, expect, it } from "vitest";
import { rasterizeOutlines } from "./rasterizeOutlines";
import { makeLabelMapFromRows } from "./testImages";
import { traceLabelMap } from "./traceLabelMap";
import type { MapDocument, TraceOptions } from "@/shared/types/strategy-map.types";

const OPTIONS: TraceOptions = { source: "manual", imageUrl: null };

function scaleRows(rows: string[], factor: number): string[] {
  return rows.flatMap((row) => {
    const wide = [...row].map((char) => char.repeat(factor)).join("");
    return Array.from({ length: factor }, () => wide);
  });
}

function roundTrip(rows: string[]) {
  const original = makeLabelMapFromRows(scaleRows(rows, 10));
  const { document } = traceLabelMap(original, {}, OPTIONS);
  return { original, document, restored: rasterizeOutlines(document) };
}

describe("rasterizeOutlines", () => {
  it("restores the original pixels for block maps", () => {
    const { original, restored } = roundTrip(["abc", "dbc"]);
    expect(Array.from(restored.labels)).toEqual(Array.from(original.labels));
  });

  it("restores an enclave and a two-piece region", () => {
    const enclave = roundTrip(["aaa", "aba", "aaa"]);
    expect(Array.from(enclave.restored.labels)).toEqual(Array.from(enclave.original.labels));
    const twoPiece = roundTrip(["aba", "aba"]);
    expect(Array.from(twoPiece.restored.labels)).toEqual(Array.from(twoPiece.original.labels));
  });

  it("keeps ids and source colours and continues the id counter", () => {
    const { document } = roundTrip(["ab"]);
    const withColor: MapDocument = {
      ...document,
      regions: document.regions.map((region, index) => ({ ...region, id: `region_0${index + 2}`, source_color: "#ff0000" })),
    };
    const restored = rasterizeOutlines(withColor);
    expect(restored.entries.map((entry) => entry.id)).toEqual(["region_02", "region_03"]);
    expect(restored.entries[0].sourceColor).toBe("#ff0000");
    expect(restored.nextIdNumber).toBe(4);
  });

  it("rejects path commands this tracer never emits", () => {
    const { document } = roundTrip(["ab"]);
    const curved: MapDocument = {
      ...document,
      regions: [{ ...document.regions[0], outline: "M0 0 C1 1 2 2 3 3 Z" }],
    };
    expect(() => rasterizeOutlines(curved)).toThrow(Error);
  });
});
