import { describe, expect, it } from "vitest";
import { calculateTacticalOdds } from "../useWarCouncilOdds";
import type { BattleOutlook, BattleView } from "../../StrategyWarCouncil.types";

const outlook: BattleOutlook = {
  own_losses: { low: 40, expected: 55, high: 70 },
  enemy_losses: { low: 90, expected: 100, high: 110 },
  own_share_percent: 62,
  confidence: "low",
  basis: "assumed_even_mix",
  factors: [
    { id: "formation", percent: 100 },
    { id: "weather", percent: 85 },
    { id: "supply", percent: 110 },
  ],
};

const baseBattle: BattleView = {
  id: "battle-1",
  region_id: "ashford_ford",
  status: "awaiting_commands",
  outcome: null,
  current_turn: 1,
  exchanges_used: 0,
  total_exchanges: 0,
  is_big: true,
  control_mode: "player",
  terrain: "hills",
  weather: "rain",
  command_cost: 1,
  opponents: [{ faction_id: "ironmark", strength: { minimum: 1200, maximum: 1600 }, reports: [] }],
  legal_commands: ["set_plan"],
};

describe("calculateTacticalOdds", () => {
  it("carries the engine's outlook through unchanged", () => {
    const odds = calculateTacticalOdds({ ...baseBattle, outlook });

    expect(odds?.balancePercent).toBe(62);
    expect(odds?.tierText).toBe("Favorable");
    expect(odds?.playerLoss).toEqual(outlook.own_losses);
    expect(odds?.enemyLoss).toEqual(outlook.enemy_losses);
    expect(odds?.confidence).toBe("low");
  });

  it("shows each engine modifier as its difference from a neutral 100%", () => {
    const odds = calculateTacticalOdds({ ...baseBattle, outlook });

    expect(odds?.factors).toEqual([
      expect.objectContaining({ id: "formation", valuePercent: 0, isPositive: true }),
      expect.objectContaining({ id: "weather", valuePercent: -15, isPositive: false }),
      expect.objectContaining({ id: "supply", valuePercent: 10, isPositive: true }),
    ]);
  });

  it("invents nothing when the engine gave no outlook", () => {
    expect(calculateTacticalOdds(baseBattle)).toBeNull();
  });
});
