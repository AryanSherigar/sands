import { describe, it, expect } from "vitest";
import { buildAnswerEventOrder, buildSituationAnswer } from "../orderBuilders";
import { describeOrder } from "../orderSummary";

describe("answer event orders", () => {
  it("builds the order the simulation expects", () => {
    expect(buildAnswerEventOrder("house_carrow", "event_1", "ease_taxes")).toEqual({
      kind: "answer_event",
      faction_id: "house_carrow",
      event_id: "event_1",
      choice_id: "ease_taxes",
    });
  });

  it("describes a queued answer in the orders tray", () => {
    const order = buildAnswerEventOrder("house_carrow", "event_1", "garrison_crackdown");
    expect(describeOrder(order)).toBe("Answer: Garrison crackdown");
  });
});

describe("buildSituationAnswer", () => {
  it("answers an uprising with a resolve_uprising order", () => {
    expect(buildSituationAnswer("house_carrow", "uprising", "uprising_ashford_4", "concessions")).toEqual({
      kind: "resolve_uprising",
      faction_id: "house_carrow",
      uprising_id: "uprising_ashford_4",
      response: "concessions",
    });
  });

  it("keeps answering events as answer_event orders", () => {
    expect(buildSituationAnswer("house_carrow", "event", "event_1", "ease_taxes").kind).toBe(
      "answer_event",
    );
  });
});
