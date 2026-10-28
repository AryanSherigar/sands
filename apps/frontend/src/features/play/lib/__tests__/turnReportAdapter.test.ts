import { describe, expect, it } from "vitest";
import { deriveTurnReport } from "../turnReportAdapter";
import { DEFAULT_PREVIEW_WORLD } from "../../components/StrategyPlayScreen/defaultPreviewWorld";
import type { BattleView, CampaignWorldView } from "../../types/simulation.types";

describe("deriveTurnReport", () => {
  const regionNames: Record<string, string> = {
    ashford: "Ashford",
    greywater_ford: "Greywater Ford",
    marrow_heath: "Marrow Heath",
    "reg-dunmere": "Dunmere",
    "reg-greenford": "Greenford",
  };

  it("calculates financial, stability, and casualty metrics from world differences", () => {
    const prevWorld: CampaignWorldView = {
      ...DEFAULT_PREVIEW_WORLD,
      my_faction: {
        ...DEFAULT_PREVIEW_WORLD.my_faction,
        treasury: 320,
        stability: 82,
        manpower: 3650,
      },
    };
    const nextWorld: CampaignWorldView = {
      ...DEFAULT_PREVIEW_WORLD,
      turn: 2,
      my_faction: {
        ...DEFAULT_PREVIEW_WORLD.my_faction,
        treasury: 298,
        stability: 78,
        manpower: 3240,
      },
    };

    const report = deriveTurnReport(prevWorld, nextWorld, regionNames);

    expect(report.turn).toBe(2);
    expect(report.quickStats.netGold).toBe(-22);
    expect(report.quickStats.stabilityDelta).toBe(-4);
    expect(report.quickStats.totalCasualties).toBe(410);
    expect(report.economyLines.length).toBeGreaterThan(0);
    expect(report.items.length).toBeGreaterThan(0);
  });

  it("provides fallback report data for turn 1 without previous world", () => {
    const report = deriveTurnReport(null, DEFAULT_PREVIEW_WORLD, regionNames);
    expect(report.turn).toBe(DEFAULT_PREVIEW_WORLD.turn);
    expect(report.quickStats.netGold).toBe(0);
    expect(report.quickStats.stabilityDelta).toBe(0);
    expect(report.quickStats.totalCasualties).toBe(0);
    expect(report.quickStats.stability).toBe(DEFAULT_PREVIEW_WORLD.my_faction.stability);
    expect(report.quickStats.manpower).toBe(DEFAULT_PREVIEW_WORLD.my_faction.manpower);
  });

  it("maps battles into structured BattleReportItem entries with tactical skirmish rounds", () => {
    const battle: BattleView = {
      id: "b-greywater",
      region_id: "greywater_ford",
      status: "resolved",
      outcome: "decisive_victory",
      exchanges_used: 2,
      total_exchanges: 4,
    };
    const worldWithBattle: CampaignWorldView = {
      ...DEFAULT_PREVIEW_WORLD,
      turn: 3,
      battles: [battle],
    };

    const report = deriveTurnReport(null, worldWithBattle, regionNames);

    expect(report.battles).toHaveLength(1);
    const battleReport = report.battles[0];
    expect(battleReport.id).toBe("b-greywater");
    expect(battleReport.regionId).toBe("greywater_ford");
    expect(battleReport.regionName).toBe("Greywater Ford");
    expect(battleReport.outcome).toBe("decisive_victory");
    expect(battleReport.rounds.length).toBeGreaterThanOrEqual(1);
    expect(battleReport.rounds[0].description).toBeDefined();
    expect(battleReport.warScoreDelta).toBeGreaterThan(0);
    expect(report.headline).toContain("Greywater Ford");
  });

  it("synthesizes dispatches for internal discontent, diplomacy, and rival actions", () => {
    const world: CampaignWorldView = {
      ...DEFAULT_PREVIEW_WORLD,
      turn: 2,
    };

    const report = deriveTurnReport(null, world, regionNames);

    const internalItems = report.items.filter((i) => i.category === "internal");
    const diplomacyItems = report.items.filter((i) => i.category === "diplomacy");

    expect(internalItems.length).toBeGreaterThan(0);
    expect(diplomacyItems.length).toBeGreaterThan(0);

    const highUnrestItem = internalItems.find((i) => i.regionId === "reg-greenford");
    expect(highUnrestItem).toBeDefined();
    expect(highUnrestItem?.badge?.tone).toBe("warning");

    const warItem = diplomacyItems.find((i) => i.badge?.tone === "danger");
    expect(warItem).toBeDefined();
  });
});
