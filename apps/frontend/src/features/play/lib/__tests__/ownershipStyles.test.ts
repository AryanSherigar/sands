import { describe, it, expect } from "vitest";
import {
  buildOwnershipFillClasses,
  buildRegionStrokeClasses,
} from "../ownershipStyles";
import {
  FOG_MODE_SHADOW_FILL_CLASS,
  FOG_MODE_VISIBLE_FILL_CLASS,
  FOGGED_FILL_CLASS,
  FOGGED_STROKE_CLASS,
  LANTERN_STROKE_CLASS,
  NEUTRAL_FILL_CLASS,
  OCCUPIED_STROKE_CLASS,
  OWN_FACTION_FILL_CLASS,
  RIVAL_FILL_CLASSES,
} from "../../constants/ownershipPalette";
import type { RegionView } from "../../types/simulation.types";

const makeRegion = (
  regionId: string,
  ownerId: string | null,
  visibility: "visible" | "fogged" = "visible",
): RegionView => ({
  region_id: regionId,
  owner_id: ownerId,
  terrain: "plain",
  visibility,
});

describe("buildOwnershipFillClasses", () => {
  it("colors own and unclaimed regions distinctly in default mode", () => {
    const fills = buildOwnershipFillClasses(
      [
        makeRegion("r1", "me"),
        makeRegion("r2", "zeta"),
        makeRegion("r3", "alpha"),
        makeRegion("r4", null),
        makeRegion("r5", "alpha"),
      ],
      "me",
    );
    expect(fills.r1).toBe(OWN_FACTION_FILL_CLASS);
    expect(fills.r4).toBe(NEUTRAL_FILL_CLASS);
    expect(fills.r3).toBe(RIVAL_FILL_CLASSES[0]);
    expect(fills.r5).toBe(fills.r3);
    expect(fills.r2).toBe(RIVAL_FILL_CLASSES[1]);
  });

  it("applies fogged fill to fogged regions not owned by player", () => {
    const fills = buildOwnershipFillClasses(
      [
        makeRegion("r1", "me", "fogged"),
        makeRegion("r2", "zeta", "fogged"),
        makeRegion("r3", null, "fogged"),
      ],
      "me",
    );
    expect(fills.r1).toBe(OWN_FACTION_FILL_CLASS);
    expect(fills.r2).toBe(FOGGED_FILL_CLASS);
    expect(fills.r3).toBe(FOGGED_FILL_CLASS);
  });

  it("uses fog mode fills when activeMapMode is fog", () => {
    const fills = buildOwnershipFillClasses(
      [
        makeRegion("r1", "me", "visible"),
        makeRegion("r2", "zeta", "fogged"),
      ],
      "me",
      "fog",
    );
    expect(fills.r1).toBe(FOG_MODE_VISIBLE_FILL_CLASS);
    expect(fills.r2).toBe(FOG_MODE_SHADOW_FILL_CLASS);
  });
});

describe("buildRegionStrokeClasses", () => {
  it("applies lantern stroke to visible or owned regions in default mode", () => {
    const strokes = buildRegionStrokeClasses(
      [
        makeRegion("r1", "me", "fogged"),
        makeRegion("r2", "zeta", "visible"),
        makeRegion("r3", "zeta", "fogged"),
      ],
      "me",
    );
    expect(strokes.r1).toBe(LANTERN_STROKE_CLASS);
    expect(strokes.r2).toBe(LANTERN_STROKE_CLASS);
    expect(strokes.r3).toBe(FOGGED_STROKE_CLASS);
  });

  it("applies strokes strictly based on visibility in fog mode", () => {
    const strokes = buildRegionStrokeClasses(
      [
        makeRegion("r1", "me", "visible"),
        makeRegion("r2", "me", "fogged"),
        makeRegion("r3", "zeta", "visible"),
        makeRegion("r4", "zeta", "fogged"),
      ],
      "me",
      "fog",
    );
    expect(strokes.r1).toBe(LANTERN_STROKE_CLASS);
    expect(strokes.r2).toBe(FOGGED_STROKE_CLASS);
    expect(strokes.r3).toBe(LANTERN_STROKE_CLASS);
    expect(strokes.r4).toBe(FOGGED_STROKE_CLASS);
  });
});

describe("occupied and besieged regions", () => {
  const occupied: RegionView = {
    ...makeRegion("r1", "zeta"),
    occupation: { occupier_id: "me", siege_progress: 100, hold_turns: 1 },
  };
  const besieged: RegionView = {
    ...makeRegion("r2", "zeta"),
    siege: { besieger_id: "me", progress: 30 },
  };

  it("outlines them distinctly in the political map", () => {
    const strokes = buildRegionStrokeClasses([occupied, besieged, makeRegion("r3", "zeta")], "me");
    expect(strokes.r1).toBe(OCCUPIED_STROKE_CLASS);
    expect(strokes.r2).toBe(OCCUPIED_STROKE_CLASS);
    expect(strokes.r3).toBe(LANTERN_STROKE_CLASS);
  });

  it("keeps the fog map outline unchanged", () => {
    const strokes = buildRegionStrokeClasses([occupied], "me", "fog");
    expect(strokes.r1).toBe(LANTERN_STROKE_CLASS);
  });
});
