import { describe, expect, it } from "vitest";
import { getCardKind, getEntityTypeForKind } from "./cardKind";

describe("cardKind mapping", () => {
  it.each([
    ["character", "character"],
    ["location", "place"],
    ["faction", "group"],
    ["organization", "group"],
    ["item", "thing"],
    ["ship", "other"],
  ])("maps entity type %s to the %s card", (entityType, kind) => {
    expect(getCardKind(entityType)).toBe(kind);
  });

  it("maps card kinds to the backend entity types", () => {
    expect(getEntityTypeForKind("place")).toBe("location");
    expect(getEntityTypeForKind("group")).toBe("faction");
    expect(getEntityTypeForKind("thing")).toBe("item");
    expect(getEntityTypeForKind("character")).toBe("character");
  });
});
