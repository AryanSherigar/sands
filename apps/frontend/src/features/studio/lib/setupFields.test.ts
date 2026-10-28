import { describe, expect, it } from "vitest";
import { NAME_SETUP_FIELD, SETUP_QUICK_ADDS } from "../constants/guideChips";
import {
  buildCustomField,
  buildQuickAddField,
  hasNameField,
  hasQuickAdd,
  removeField,
  renameOption,
  toFieldKey,
} from "./setupFields";

const difficulty = SETUP_QUICK_ADDS.find((chip) => chip.id === "difficulty")!;
const pronouns = SETUP_QUICK_ADDS.find((chip) => chip.id === "pronouns")!;

describe("setupFields", () => {
  it("builds the Difficulty field with Gentle, Normal and Harsh and Normal as default", () => {
    const field = buildQuickAddField(difficulty, [NAME_SETUP_FIELD]);
    expect(field.type).toBe("single_select");
    expect(field.options.map((option) => option.label)).toEqual(["Gentle", "Normal", "Harsh"]);
    expect(field.defaultValue).toBe("normal");
  });

  it("offers she, he, they and their own for Pronouns", () => {
    const field = buildQuickAddField(pronouns, []);
    expect(field.options.map((option) => option.label)).toEqual(["She", "He", "They", "Their own"]);
  });

  it("keeps field keys unique", () => {
    const first = buildQuickAddField(difficulty, []);
    expect(toFieldKey("Difficulty", [first])).toBe("difficulty_2");
    expect(buildCustomField([first]).key).toBe("your_own");
  });

  it("knows which quick adds and the name field are already present", () => {
    const fields = [NAME_SETUP_FIELD, buildQuickAddField(difficulty, [])];
    expect(hasNameField(fields)).toBe(true);
    expect(hasQuickAdd(fields, difficulty)).toBe(true);
    expect(hasQuickAdd(fields, pronouns)).toBe(false);
    expect(hasNameField(removeField(fields, NAME_SETUP_FIELD.id))).toBe(false);
  });

  it("renames an option and keeps its value in step", () => {
    const field = buildQuickAddField(difficulty, []);
    const renamed = renameOption(field.options, field.options[0].id, "Very Gentle");
    expect(renamed[0]).toMatchObject({ label: "Very Gentle", value: "very_gentle" });
  });
});
