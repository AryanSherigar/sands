import { describe, expect, it } from "vitest";
import { buildWardsFromContingent } from "../warCouncilWards";

const sumWardCounts = (wards: ReturnType<typeof buildWardsFromContingent>): number =>
  Object.values(wards)
    .flatMap((ward) => ward.ranks)
    .reduce((total, cohort) => total + cohort.count, 0);

describe("buildWardsFromContingent", () => {
  it("distributes exactly the active troops across the three wards", () => {
    const wards = buildWardsFromContingent({ infantry: 165, cavalry: 30 });
    expect(sumWardCounts(wards)).toBe(195);
  });

  it("gives the center ward the remainder of an uneven split", () => {
    const wards = buildWardsFromContingent({ infantry: 100 });
    expect(wards.left.ranks[0].count).toBe(33);
    expect(wards.right.ranks[0].count).toBe(33);
    expect(wards.center.ranks[0].count).toBe(34);
  });

  it("omits troop types the contingent does not have", () => {
    const wards = buildWardsFromContingent({ infantry: 90 });
    const troopTypes = wards.center.ranks.map((cohort) => cohort.troopType);
    expect(troopTypes).toEqual(["infantry"]);
  });

  it("marks only the center ward as the tactic anchor", () => {
    const wards = buildWardsFromContingent({ infantry: 90 });
    expect([wards.left.isAnchor, wards.center.isAnchor, wards.right.isAnchor]).toEqual([
      false,
      true,
      false,
    ]);
  });
});
