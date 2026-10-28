import { describe, expect, it } from "vitest";
import type { StateFieldDefinition } from "../types/scenario.types";
import {
  applyPlayerSees,
  changeKind,
  listPlayerSeesChoices,
  readPlayerSees,
  renameField,
  setBound,
  setOptions,
} from "./trackedValueEditing";

const HEALTH: StateFieldDefinition = { type: "number", label: "Health", min: 0, max: 10, initial: 10 };
const FREE: { isClockTaken: boolean; isLevelsTaken: boolean } = { isClockTaken: false, isLevelsTaken: false };

describe("trackedValueEditing", () => {
  it("reads what the player sees from the real hint keys", () => {
    expect(readPlayerSees(HEALTH)).toBe("plain");
    expect(readPlayerSees({ ...HEALTH, hidden: true })).toBe("hidden");
    expect(readPlayerSees({ ...HEALTH, display: { kind: "meter" } })).toBe("bar");
    expect(readPlayerSees({ ...HEALTH, display: { kind: "meter", tiers: [] } })).toBe("levels");
    expect(readPlayerSees({ ...HEALTH, display: { kind: "clock" } })).toBe("clock");
    expect(readPlayerSees({ type: "enum", display: { kind: "tier" } })).toBe("levels");
  });

  it("builds a meter from the lowest and highest values", () => {
    expect(applyPlayerSees(HEALTH, "bar").display).toEqual({
      kind: "meter",
      label: "Health",
      clamp_min: 0,
      clamp_max: 10,
    });
  });

  it("builds levels, a clock, a tier and a hidden flag, never both display and hidden", () => {
    const levels = applyPlayerSees(HEALTH, "levels").display as { tiers: unknown[] };
    expect(levels.tiers.length).toBeGreaterThan(1);
    expect(applyPlayerSees(HEALTH, "clock").display).toMatchObject({ kind: "clock", start: "09:00", format: "12h" });
    expect(applyPlayerSees({ type: "enum", label: "Time", options: ["Day"] }, "levels").display).toEqual({
      kind: "tier",
      label: "Time",
    });
    const hidden = applyPlayerSees({ ...HEALTH, display: { kind: "meter" } }, "hidden");
    expect(hidden).toMatchObject({ hidden: true });
    expect(hidden.display).toBeUndefined();
    expect(applyPlayerSees({ ...HEALTH, hidden: true }, "bar").hidden).toBeUndefined();
  });

  it("only offers a bar or levels when the value has a lowest and a highest", () => {
    const noMax = { type: "number" as const, label: "Money", min: 0 };
    const offered = listPlayerSeesChoices(noMax, FREE)
      .filter((choice) => !choice.isDisabled)
      .map((choice) => choice.value);
    expect(offered).toEqual(["plain", "clock", "hidden"]);
  });

  it("does not offer a second clock or a second tier", () => {
    const taken = { isClockTaken: true, isLevelsTaken: true };
    expect(listPlayerSeesChoices(HEALTH, taken).find((choice) => choice.value === "clock")?.isDisabled).toBe(true);
    expect(listPlayerSeesChoices({ type: "enum" }, taken).find((choice) => choice.value === "levels")?.isDisabled).toBe(true);
  });

  it("keeps the shown name and bar in step with the value", () => {
    const shown = applyPlayerSees(HEALTH, "bar");
    expect(renameField(shown, "Vitality").display).toMatchObject({ label: "Vitality" });
    expect(setBound(shown, "max", 20).display).toMatchObject({ clamp_max: 20 });
    expect(setBound(shown, "max", undefined).display).toBeUndefined();
    expect(setBound(HEALTH, "max", 5).initial).toBe(5);
  });

  it("keeps the starting choice among the options", () => {
    const time: StateFieldDefinition = { type: "enum", options: ["Dawn", "Day"], initial: "Day" };
    expect(setOptions(time, ["Night", "Dusk"]).initial).toBe("Night");
    expect(setOptions(time, ["Day", "Dusk"]).initial).toBe("Day");
  });

  it("changes the type while keeping the name and what it means", () => {
    const next = changeKind({ ...HEALTH, description: "Hit points" }, "boolean");
    expect(next).toMatchObject({ type: "boolean", label: "Health", description: "Hit points", initial: false });
    expect(next.min).toBeUndefined();
  });
});
