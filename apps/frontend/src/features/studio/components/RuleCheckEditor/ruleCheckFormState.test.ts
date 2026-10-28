import { describe, expect, it } from "vitest";
import {
  buildEmptyOption,
  buildInitialState,
  buildPayload,
  getFormProblems,
} from "./ruleCheckFormState";
import type { RuleCheckResponse } from "../../types/ruleCheck.types";

const RESULTS = ["held", "moved", "timeout"];

const savedCheck: RuleCheckResponse = {
  check_id: "c1",
  scenario_id: "s1",
  label: "Lamp-out",
  kind: "timed_choice",
  trigger_condition_expression: { field: "cabin.lamp", op: "==", value: "out" },
  priority: 0,
  result_path: "check.lamp",
  narrator_instruction_template: null,
  params: {
    prompt: "The lamp has gone out.",
    options: [
      { id: "hold", label: "Hold still", result: "held", mutations: [], reopens: false },
      { id: "move", label: "Move away", result: "moved", mutations: [], reopens: false },
    ],
    window_ms: 12000,
    timeout_result: "timeout",
    hidden_result: "moved",
    max_reopens: 3,
  },
};

describe("ruleCheckFormState", () => {
  it("round-trips a saved timed choice, converting the window to seconds and back", () => {
    const state = buildInitialState(savedCheck);

    expect(state.timed.windowSeconds).toBe(12);
    const payload = buildPayload(state);

    expect(payload.params).toMatchObject({
      window_ms: 12000,
      timeout_result: "timeout",
      hidden_result: "moved",
    });
    expect(payload.result_path).toBe("check.lamp");
  });

  it("sends a blank hidden result as null", () => {
    const state = buildInitialState(savedCheck);
    state.timed.hiddenResult = "";

    expect(
      (buildPayload(state).params as { hidden_result: string | null }).hidden_result,
    ).toBeNull();
  });

  it("accepts a saved check and rejects an empty new one", () => {
    expect(getFormProblems(buildInitialState(savedCheck), RESULTS)).toEqual([]);
    expect(getFormProblems(buildInitialState(null), RESULTS).length).toBeGreaterThan(0);
  });

  it("reports a result that is not an option of the chosen field", () => {
    const state = buildInitialState(savedCheck);
    state.timed.options[0].result = "levitated";

    expect(getFormProblems(state, RESULTS)).toContain(
      "Every option needs a result from the chosen field.",
    );
  });

  it("reports duplicate option ids and a window outside 1 to 120 seconds", () => {
    const state = buildInitialState(savedCheck);
    state.timed.options[1] = { ...buildEmptyOption(1), id: "hold", label: "x", result: "moved" };
    state.timed.windowSeconds = 0.5;

    const problems = getFormProblems(state, RESULTS);

    expect(problems).toContain("Option ids must be unique.");
    expect(problems).toContain("The window must be between 1 and 120 seconds.");
  });

  it("validates recall wordings", () => {
    const state = buildInitialState(null);
    state.kind = "recall";
    state.label = "Recall";
    state.resultPath = "check.recall";
    state.recall = {
      ...state.recall,
      prompt: "Which?",
      variants: ["same", "same"],
      resultCorrect: "held",
      resultWrong: "moved",
      resultTimeout: "timeout",
    };

    expect(getFormProblems(state, RESULTS)).toContain(
      "Wordings must be different from each other.",
    );
  });
});
