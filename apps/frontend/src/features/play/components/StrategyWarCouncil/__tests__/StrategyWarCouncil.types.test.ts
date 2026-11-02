import { describe, expect, it } from "vitest";
import type {
  WardConfig,
  WardRankCohort,
  HistoricalDoctrine,
} from "../StrategyWarCouncil.types";

describe("StrategyWarCouncil Types", () => {
  it("constructs valid WardConfig with 3 rank tiers", () => {
    const cohort: WardRankCohort = {
      id: "c-spears-1",
      troopType: "infantry",
      name: "Shieldwall Spearmen",
      count: 600,
      rankOrder: "front",
      tacticalRole: "Locks shields and braces against shock charges",
    };

    const ward: WardConfig = {
      ward: "center",
      title: "Center (Main Battle)",
      stance: "hold",
      isAnchor: true,
      ranks: [cohort],
    };

    expect(ward.ward).toBe("center");
    expect(ward.ranks[0].rankOrder).toBe("front");
    expect(ward.ranks[0].count).toBe(600);
  });

  it("constructs historical doctrine with terrain requirements", () => {
    const doctrine: HistoricalDoctrine = {
      id: "feigned_retreat",
      name: "Feigned Retreat",
      latinName: "Simulata Fuga",
      summary: "Front rank yields ground into bottleneck; rear knights wheel to envelop.",
      risk: "Catastrophic collapse if front rank routs for real.",
    };
    expect(doctrine.id).toBe("feigned_retreat");
  });
});
