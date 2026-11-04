import { describe, expect, it } from "vitest";
import type { ExchangeReport } from "../../components/StrategyWarCouncil/StrategyWarCouncil.types";
import {
  withLiveEnemyEstimate,
  withLiveEnemyEstimateOnLatest,
} from "../battleReports";

const buildReport = (totalExchange: number, minimum: number, maximum: number): ExchangeReport => ({
  battle_id: "battle-1",
  campaign_turn: 1,
  exchange_index: totalExchange,
  total_exchange: totalExchange,
  own_losses: { infantry: 10 },
  opponent_strength: { minimum, maximum },
  outcome: null,
});

describe("withLiveEnemyEstimate", () => {
  it("adopts a tighter live estimate over the report's wider range", () => {
    const refined = withLiveEnemyEstimate(buildReport(1, 0, 512), { minimum: 306, maximum: 374 });
    expect(refined.opponent_strength).toEqual({ minimum: 306, maximum: 374 });
  });

  it("keeps the report range when the live estimate is wider", () => {
    const report = buildReport(1, 300, 320);
    expect(withLiveEnemyEstimate(report, { minimum: 0, maximum: 512 })).toBe(report);
  });

  it("keeps the report when no live estimate exists", () => {
    const report = buildReport(1, 0, 512);
    expect(withLiveEnemyEstimate(report, undefined)).toBe(report);
  });
});

describe("withLiveEnemyEstimateOnLatest", () => {
  it("refines only the latest report and leaves earlier snapshots", () => {
    const earlier = buildReport(1, 0, 512);
    const latest = buildReport(2, 0, 512);
    const result = withLiveEnemyEstimateOnLatest([earlier, latest], { minimum: 306, maximum: 374 });
    expect(result[0]).toBe(earlier);
    expect(result[1].opponent_strength).toEqual({ minimum: 306, maximum: 374 });
  });
});
