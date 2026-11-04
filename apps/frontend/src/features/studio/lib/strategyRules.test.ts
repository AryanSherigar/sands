import { describe, expect, it } from "vitest";
import { applyStrategyFields, readStrategyFields } from "./strategyDocument";
import { setRules } from "./strategyRules";

describe("strategy rules", () => {
  it("reads defaults from an empty document", () => {
    expect(readStrategyFields({}).rules.trade_income_percent).toBe(10);
  });

  it("round-trips edited rules and keeps unrelated tuning keys", () => {
    const raw = { tuning: { end_year: 1004, agents: { loyalty_min: 25 }, overtures: { cooldown_turns: 6 } } };
    const edited = setRules(readStrategyFields(raw), { agents_enabled: true, oath_offer_min_opinion: 35 });

    const written = applyStrategyFields(raw, edited) as { tuning: Record<string, Record<string, unknown>> };

    expect(written.tuning.agents).toMatchObject({ loyalty_min: 25, is_enabled: true });
    expect(written.tuning.overtures).toMatchObject({ cooldown_turns: 6, oath_offer_min_opinion: 35 });
    expect(readStrategyFields(written).rules.oath_offer_min_opinion).toBe(35);
  });

  it("writes the revolt talk switch into its own tuning block", () => {
    const edited = setRules(readStrategyFields({ tuning: { end_year: 1004 } }), { revolt_talks_enabled: true });
    const written = applyStrategyFields({ tuning: { end_year: 1004 } }, edited) as { tuning: { revolt_talk: unknown } };

    expect(written.tuning.revolt_talk).toEqual({ is_enabled: true });
  });
});
