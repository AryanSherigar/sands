import { describe, expect, it } from "vitest";
import type { MapRegion } from "@/shared/types/strategy-map.types";
import { buildStrategyChatContext } from "./strategyChatContext";
import { addFaction, readStrategyFields, setRegionOwner } from "./strategyDocument";

const MAP_REGION: MapRegion = {
  id: "north",
  name: "North Reach",
  terrain: "plain",
  outline: "M0 0",
  label_point: { x: 1, y: 1 },
  neighbor_ids: [],
  source_color: null,
  source_ref: null,
};

describe("buildStrategyChatContext", () => {
  it("lists factions with their ruler, regions with names and owners, and the open panel", () => {
    const withFaction = addFaction(readStrategyFields({}), "Ashford");
    const fields = setRegionOwner(withFaction, "north", "ashford");

    const context = buildStrategyChatContext({ title: "The Reach", fields, mapRegions: [MAP_REGION], activePanel: "relations" });

    expect(context.title).toBe("The Reach");
    expect(context.active_panel).toBe("relations");
    expect(context.factions[0]).toMatchObject({ faction_id: "ashford", leader_id: "ashford_ruler", leader_name: "Ruler of Ashford" });
    expect(context.regions).toEqual([expect.objectContaining({ region_id: "north", name: "North Reach", owner_id: "ashford" })]);
    expect(context.armies).toHaveLength(1);
  });

  it("includes unowned map regions and tolerates an empty document", () => {
    const context = buildStrategyChatContext({ title: "", fields: readStrategyFields({}), mapRegions: [MAP_REGION], activePanel: null });

    expect(context.factions).toEqual([]);
    expect(context.regions).toEqual([expect.objectContaining({ region_id: "north", owner_id: null })]);
    expect(context.active_panel).toBe("");
  });
});
