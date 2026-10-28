import { describe, expect, it } from "vitest";
import { deriveTurnReport } from "../turnReportAdapter";
import { mapApiOutcome, mergeTurnReport } from "../turnReportMerge";
import { DEFAULT_PREVIEW_WORLD } from "../../components/StrategyPlayScreen/defaultPreviewWorld";
import { ALL_ESTIMATED_SECTIONS } from "../../constants/turnReportGaps";
import type { ApiBattleReport, TurnReportResponse } from "../../types/turnReportApi.types";

const REGION_NAMES = { "reg-dunmere": "Dunmere" };

const battle = (overrides: Partial<ApiBattleReport> = {}): ApiBattleReport => ({
  battle_id: "b1",
  region_id: "reg-dunmere",
  outcome: "attacker_victory",
  own_side: "attacker",
  exchanges: 2,
  own_losses: { infantry: 150, cavalry: 50 },
  rounds: [
    { total_exchange: 1, own_losses: 120 },
    { total_exchange: 2, own_losses: 80 },
  ],
  ...overrides,
});

const response = (overrides: Partial<TurnReportResponse> = {}): TurnReportResponse => ({
  turn: 0,
  net_gold: 30,
  economy: [
    { kind: "income_collected", category: "tax", amount: 60, subject_ids: [], inputs: { tax_percent: 25 } },
    { kind: "upkeep_paid", category: "upkeep", amount: -30, subject_ids: [], inputs: {} },
  ],
  battles: [],
  lines: [{ text_key: "tax_rate_set", kind: "tax_rate_set", subject_ids: [] }],
  major_event_kinds: [],
  ...overrides,
});

const estimated = deriveTurnReport(null, DEFAULT_PREVIEW_WORLD, REGION_NAMES);

describe("mergeTurnReport", () => {
  it("replaces estimated economy and net gold with the backend's figures", () => {
    const report = mergeTurnReport(estimated, response(), DEFAULT_PREVIEW_WORLD, REGION_NAMES);
    expect(report.quickStats.netGold).toBe(30);
    expect(report.economyLines).toEqual([
      { label: "Provincial Taxes", amount: 60, category: "tax", details: "25% tax rate" },
      { label: "Military Upkeep", amount: -30, category: "upkeep", details: undefined },
    ]);
  });

  it("builds battles from real losses and keeps estimated round text", () => {
    const report = mergeTurnReport(
      estimated,
      response({ battles: [battle()] }),
      DEFAULT_PREVIEW_WORLD,
      REGION_NAMES,
    );
    const [merged] = report.battles;
    expect(merged.varnLosses).toBe(200);
    expect(merged.rounds.map((round) => round.varnCasualties)).toEqual([120, 80]);
    expect(report.quickStats.totalCasualties).toBe(200);
    expect(merged.regionName).toBe("Dunmere");
  });

  it("lists only the sections that are still estimated", () => {
    const report = mergeTurnReport(estimated, response({ battles: [battle()] }), DEFAULT_PREVIEW_WORLD, REGION_NAMES);
    expect(report.estimatedSections).toContain("stability_delta");
    expect(report.estimatedSections).toContain("victory_margin");
    expect(report.estimatedSections).not.toContain("economy_lines");
  });

  it("omits the victory margin gap when no battle was fought", () => {
    const report = mergeTurnReport(estimated, response(), DEFAULT_PREVIEW_WORLD, REGION_NAMES);
    expect(report.estimatedSections).not.toContain("victory_margin");
  });

  it("turns recorded events into dispatches and ignores unknown kinds", () => {
    const report = mergeTurnReport(
      estimated,
      response({
        lines: [
          { text_key: "x", kind: "tax_rate_set", subject_ids: [] },
          { text_key: "y", kind: "army_moved", subject_ids: [] },
        ],
      }),
      DEFAULT_PREVIEW_WORLD,
      REGION_NAMES,
    );
    expect(report.items.filter((item) => item.id.startsWith("event-"))).toHaveLength(1);
  });
});

describe("mapApiOutcome", () => {
  it.each([
    ["attacker_victory", "attacker", "marginal_victory"],
    ["defender_victory", "attacker", "defeat"],
    ["defender_victory", "defender", "marginal_victory"],
    ["defender_surrender", "attacker", "decisive_victory"],
    ["attacker_surrender", "attacker", "defeat"],
    ["mutual_disengagement", "defender", "stalemate"],
    [null, "attacker", "stalemate"],
  ] as const)("maps %s for the %s side to %s", (outcome, ownSide, expected) => {
    expect(mapApiOutcome(battle({ outcome, own_side: ownSide }))).toBe(expected);
  });
});

describe("deriveTurnReport estimates", () => {
  it("marks every section as estimated", () => {
    expect(estimated.estimatedSections).toEqual(ALL_ESTIMATED_SECTIONS);
  });
});
