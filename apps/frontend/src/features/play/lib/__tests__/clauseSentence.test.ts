import { describe, expect, it } from "vitest";
import { composeClauseSentence, type ClauseDraft } from "../clauseSentence";

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
