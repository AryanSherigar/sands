import { describe, it, expect } from "vitest";
import { buildOwnershipFillClasses } from "../ownershipStyles";
import {
  NEUTRAL_FILL_CLASS,
  OWN_FACTION_FILL_CLASS,
  RIVAL_FILL_CLASSES,
} from "../../constants/ownershipPalette";
import type { RegionView } from "../../types/simulation.types";

const region = (regionId: string, ownerId: string | null): RegionView => ({
  region_id: regionId,
  owner_id: ownerId,
  terrain: "plain",
  visibility: "visible",
});

describe("buildOwnershipFillClasses", () => {
  const fills = buildOwnershipFillClasses(
    [region("r1", "me"), region("r2", "zeta"), region("r3", "alpha"), region("r4", null), region("r5", "alpha")],
    "me",
  );

  it("colors own and unclaimed regions distinctly", () => {
    expect(fills.r1).toBe(OWN_FACTION_FILL_CLASS);
    expect(fills.r4).toBe(NEUTRAL_FILL_CLASS);
  });

  it("gives each rival a stable color shared across its regions", () => {
    expect(fills.r3).toBe(RIVAL_FILL_CLASSES[0]);
    expect(fills.r5).toBe(fills.r3);
    expect(fills.r2).toBe(RIVAL_FILL_CLASSES[1]);
  });
});
