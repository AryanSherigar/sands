import { describe, expect, it } from "vitest";
import { RuleCheckEventPayload } from "@/shared/types/check.types";
import { toActiveRuleCheck } from "./ruleCheckTiming";

const ISSUED_AT = 1_760_000_000_000;
const check: RuleCheckEventPayload = {
  check_id: "chk-1",
  kind: "timed_choice",
  prompt: "The phone rings.",
  options: [],
  window_ms: 12000,
  issued_at: ISSUED_AT,
};

describe("toActiveRuleCheck", () => {
  it("gives a freshly opened prompt its whole window", () => {
    const active = toActiveRuleCheck(check, null, 500);

    expect(active.initial_remaining_ms).toBe(12000);
    expect(active.started_at_client_ms).toBe(500);
  });

  it("subtracts the time that passed on the server clock", () => {
    expect(
      toActiveRuleCheck(check, ISSUED_AT + 5000, 0).initial_remaining_ms,
    ).toBe(7000);
  });

  it("never goes below zero", () => {
    expect(
      toActiveRuleCheck(check, ISSUED_AT + 99_000, 0).initial_remaining_ms,
    ).toBe(0);
  });

  it("never exceeds the window when the server clock is behind issued_at", () => {
    expect(
      toActiveRuleCheck(check, ISSUED_AT - 2000, 0).initial_remaining_ms,
    ).toBe(12000);
  });

  it("keeps the payload fields", () => {
    expect(toActiveRuleCheck(check, null, 0).prompt).toBe("The phone rings.");
  });
});
