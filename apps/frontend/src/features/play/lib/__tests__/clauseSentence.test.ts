import { describe, expect, it } from "vitest";
import { composeCardSentence, composeClauseSentence, type ClauseDraft } from "../clauseSentence";

const BASE: ClauseDraft = {
  mode: "trigger",
  kind: "payment",
  amount: 50,
  template: "treasury_below",
  subject: "mine",
  value: 100,
  expiresInTurns: 10,
};

describe("composeClauseSentence", () => {
  it("writes a trigger as 'Once ..., ...'", () => {
    expect(composeClauseSentence(BASE)).toBe(
      "Once my treasury is below 100 gold, I will pay you 50 gold. Let this agreement lapse after 10 turns.",
    );
  });

  it("writes a gate as 'only while ...'", () => {
    const sentence = composeClauseSentence({ ...BASE, mode: "gate", kind: "military_access", subject: "yours", template: "stability_below", value: 40 });

    expect(sentence).toBe(
      "I will grant you military access through my lands, but only while your stability is below 40. Let this agreement lapse after 10 turns.",
    );
  });

  it("drops the owner for a turn condition and clamps the lapse to 1 to 40 turns", () => {
    expect(composeClauseSentence({ ...BASE, template: "turn_after", value: 12, expiresInTurns: 99 })).toContain("turn 12 has passed");
    expect(composeClauseSentence({ ...BASE, template: "turn_after", value: 12, expiresInTurns: 99 })).toContain("after 40 turns");
    expect(composeClauseSentence({ ...BASE, expiresInTurns: 0 })).toContain("after 1 turn.");
  });
});

describe("composeCardSentence and region clauses", () => {
  it("writes an unconditional clause without a condition or a lapse", () => {
    expect(composeClauseSentence({ ...BASE, mode: "none", kind: "pact", amount: 8 })).toBe(
      "We will keep a non-aggression pact for 8 turns.",
    );
  });

  it("names the region in a region clause and a region condition", () => {
    const sentence = composeClauseSentence({
      ...BASE,
      kind: "region_promise",
      template: "loses_region",
      subject: "yours",
      regionId: "dunmere",
      regionName: "Dunmere",
    });

    expect(sentence).toBe(
      "Once your realm no longer holds Dunmere, I swear never to occupy Dunmere. Let this agreement lapse after 10 turns.",
    );
  });

  it("joins several clauses into one proposal for the ruler to weigh together", () => {
    const sentence = composeCardSentence([
      { ...BASE, mode: "none", kind: "trade_deal" },
      { ...BASE, mode: "none", kind: "cede_region", regionName: "Elmstead" },
    ]);

    expect(sentence).toBe("We will keep a trade deal. I will hand Elmstead over to you.");
  });
});
