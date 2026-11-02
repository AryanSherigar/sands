import { describe, expect, it } from "vitest";
import { calculateTacticalOdds } from "../useWarCouncilOdds";
import type { BattleView, StandingPlan } from "../../StrategyWarCouncil.types";

const mockBattle: BattleView = {
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
  own_contingent: {
    faction_id: "valenreach",
    army_ids: ["army-1"],
    troops: { infantry: 1400, cavalry: 300, archers_siege: 650 },
    morale: 95,
    fatigue: 10,
    plan: {
      formation: "defensive",
      tactic: "hold",
      withdrawal_policy: "balanced",
      reserve_policy: "conserve",
    },
    supply: "supplied",
    status: "fighting",
  },
  opponents: [
    {
      faction_id: "ironmark",
      strength: { minimum: 1200, maximum: 1600 },
      reports: [],
    },
  ],
  legal_commands: ["set_plan", "reconnoitre", "withdraw", "surrender"],
};

describe("calculateTacticalOdds", () => {
  it("calculates favorable balance with itemized terrain, weather, and trait factors", () => {
    const plan: StandingPlan = {
      formation: "defensive",
      tactic: "hold",
      withdrawal_policy: "balanced",
      reserve_policy: "conserve",
    };

    const odds = calculateTacticalOdds(mockBattle, plan, "cautious");

    expect(odds.balancePercent).toBeGreaterThan(50);
    expect(odds.factors).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ id: "terrain", isPositive: true }),
        expect.objectContaining({ id: "weather", isPositive: false }),
        expect.objectContaining({ id: "commander", isPositive: true }),
        expect.objectContaining({ id: "supply", isPositive: true }),
      ]),
    );
  });

  it("exposes interval range when opponent strength is not scouted", () => {
    const plan = mockBattle.own_contingent!.plan;
    const odds = calculateTacticalOdds(mockBattle, plan);

    expect(odds.isRange).toBe(true);
    expect(odds.minPercent).toBeLessThan(odds.maxPercent);
  });
});
