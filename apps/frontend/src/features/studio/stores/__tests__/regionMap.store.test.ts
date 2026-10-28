import { beforeEach, describe, expect, it } from "vitest";
import { mergeRegions, paintBrush } from "@/shared/lib/map-tracing/editOps";
import { makeLabelMapFromRows } from "@/shared/lib/map-tracing/testImages";
import { traceLabelMap } from "@/shared/lib/map-tracing/traceLabelMap";
import { useRegionMapStore } from "../regionMap.store";

const initial = useRegionMapStore.getState();
const store = () => useRegionMapStore.getState();

beforeEach(() => useRegionMapStore.setState(initial, true));

function load(rows: string[]): void {
  store().loadFromTrace(makeLabelMapFromRows(rows));
}

describe("regionMap store", () => {
  it("starts empty after loadFromTrace with no history", () => {
    load(["ab"]);
    expect(store().labelMap?.entries).toHaveLength(2);
    expect(store().past).toHaveLength(0);
  });

  it("undoes and redoes an edit, and clears redo on a new edit", () => {
    load(["aab", "aab"]);
    const original = store().labelMap;
    store().applyEdit(mergeRegions(original!, "region_01", "region_02"));
    expect(store().labelMap?.entries).toHaveLength(1);
    store().undo();
    expect(store().labelMap).toBe(original);
    store().redo();
    expect(store().labelMap?.entries).toHaveLength(1);
    store().undo();
    store().applyEdit(paintBrush(original!, { x: 0, y: 0 }, 0, "region_02"));
    expect(store().future).toHaveLength(0);
  });

  it("keeps at most 30 undo steps", () => {
    load(["aaab"]);
    for (let step = 0; step < 35; step++) {
      store().applyEdit(paintBrush(store().labelMap!, { x: 0, y: 0 }, 0, step % 2 ? "region_01" : "region_02"));
    }
    expect(store().past).toHaveLength(30);
  });

  it("drops meta, capital and selection of a region that an edit removes", () => {
    load(["aab", "aab"]);
    store().setMeta("region_02", { name: "Gone", terrain: "hills" });
    store().toggleCapital("region_02");
    store().select("region_02");
    store().applyEdit(mergeRegions(store().labelMap!, "region_01", "region_02"));
    expect(store().meta.region_02).toBeUndefined();
    expect(store().capitalRegionIds).toEqual([]);
    expect(store().selectedId).toBeNull();
  });

  it("applies one terrain to many regions", () => {
    load(["abc"]);
    store().setBulkTerrain(["region_01", "region_03"], "forest");
    expect(store().meta.region_01.terrain).toBe("forest");
    expect(store().meta.region_03.terrain).toBe("forest");
    expect(store().meta.region_02).toBeUndefined();
  });

  it("toggles a capital on and off", () => {
    load(["ab"]);
    store().toggleCapital("region_01");
    expect(store().capitalRegionIds).toEqual(["region_01"]);
    store().toggleCapital("region_01");
    expect(store().capitalRegionIds).toEqual([]);
  });

  it("restores editing state from a saved document", () => {
    const map = makeLabelMapFromRows(["aaaaab", "aaaaab"]);
    const meta = { region_01: { name: "Ashford", terrain: "hills" as const } };
    const { document } = traceLabelMap(map, meta, { source: "manual", imageUrl: null });
    store().loadFromDocument(document);
    expect(store().labelMap?.entries.map((entry) => entry.id)).toEqual(["region_01", "region_02"]);
    expect(store().meta.region_01).toEqual({ name: "Ashford", terrain: "hills" });
  });

  it("restores the names of a merged-away region on undo and keeps later names", () => {
    load(["aab", "aab", "ccc"]);
    store().setMeta("region_01", { name: "Alpha", terrain: "hills" });
    store().setMeta("region_02", { name: "Beta", terrain: "forest" });
    store().applyEdit(mergeRegions(store().labelMap!, "region_01", "region_02"));
    store().setMeta("region_03", { name: "Gamma", terrain: "coast" });
    store().undo();
    expect(store().meta.region_02).toEqual({ name: "Beta", terrain: "forest" });
    expect(store().meta.region_03).toEqual({ name: "Gamma", terrain: "coast" });
  });

  it("forgets everything on reset", () => {
    load(["ab"]);
    store().setMeta("region_01", { name: "Alpha", terrain: null });
    store().reset();
    expect(store().labelMap).toBeNull();
    expect(store().meta).toEqual({});
  });
});
