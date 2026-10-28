import { describe, expect, it } from "vitest";
import { toEntityTypeKey } from "./entityTypeKey";

describe("toEntityTypeKey", () => {
  it("turns a plain name into a valid type key", () => {
    expect(toEntityTypeKey("Sea Creature")).toBe("sea_creature");
    expect(toEntityTypeKey("  Ship!  ")).toBe("ship");
  });

  it("never starts with a digit or underscore and stays within 30 characters", () => {
    expect(toEntityTypeKey("3rd event")).toBe("rd_event");
    expect(toEntityTypeKey("a".repeat(60))).toHaveLength(30);
    expect(toEntityTypeKey("a".repeat(60))).toMatch(/^[a-z][a-z0-9_]{0,29}$/);
  });

  it("falls back when nothing usable is left", () => {
    expect(toEntityTypeKey("!!!")).toBe("other");
  });

  it("avoids the built-in type names", () => {
    expect(toEntityTypeKey("Character")).toBe("character_type");
  });
});
