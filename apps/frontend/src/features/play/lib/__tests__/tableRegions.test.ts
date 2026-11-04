import { describe, expect, it } from "vitest";
import { parseTableRegions } from "../tableRegions";

describe("parseTableRegions", () => {
  it("reads the regions at the table with readable names", () => {
    const regions = parseTableRegions([
      { label: "Longest pact", value: "12 turns" },
      { label: "Regions at the table", value: "carrow_vale, high-meadow" },
    ]);

    expect(regions).toEqual([
      { id: "carrow_vale", name: "Carrow Vale" },
      { id: "high-meadow", name: "High Meadow" },
    ]);
  });

  it("is empty when the scene lists no regions", () => {
    expect(parseTableRegions([{ label: "Longest pact", value: "12 turns" }])).toEqual([]);
  });
});
