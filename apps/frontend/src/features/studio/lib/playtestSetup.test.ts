import { describe, expect, it } from "vitest";
import { NAME_SETUP_FIELD } from "../constants/guideChips";
import type { SetupInputField } from "@/shared/types/scenario.types";
import {
  buildInitialSetupValues,
  getMissingRequiredFields,
  needsSetupForm,
  readOpeningText,
} from "./playtestSetup";

const difficulty: SetupInputField = {
  id: "d",
  key: "difficulty",
  label: "Difficulty",
  type: "single_select",
  required: true,
  options: [{ id: "o1", label: "Normal", value: "normal" }],
  defaultValue: "normal",
};

describe("playtestSetup", () => {
  it("needs no form when only the name field exists", () => {
    expect(needsSetupForm([NAME_SETUP_FIELD])).toBe(false);
    expect(needsSetupForm([])).toBe(false);
    expect(needsSetupForm([NAME_SETUP_FIELD, difficulty])).toBe(true);
  });

  it("fills the name with Tester and other fields with their defaults", () => {
    expect(buildInitialSetupValues([NAME_SETUP_FIELD, difficulty])).toEqual({
      character_name: "Tester",
      difficulty: "normal",
    });
  });

  it("lists required fields that are still empty", () => {
    const empty = { ...difficulty, defaultValue: "" };
    const values = buildInitialSetupValues([empty]);
    expect(getMissingRequiredFields([empty], values)).toEqual([empty]);
    expect(getMissingRequiredFields([empty], { difficulty: "harsh" })).toEqual([]);
  });

  it("prefers the rendered opening on the playthrough state over the snapshot", () => {
    expect(
      readOpeningText({
        state: { narrative: { opening_prompt: "Hello, Tester." } },
        scenario_snapshot: { opening_scene: "Hello, {player_name}." },
      }),
    ).toBe("Hello, Tester.");
    expect(readOpeningText({ scenario_snapshot: { opening_scene: "Raw." } })).toBe("Raw.");
    expect(readOpeningText({})).toBe("");
  });
});
