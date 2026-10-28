import { describe, expect, it } from "vitest";
import {
  parseDiscoverFilters,
  serializeDiscoverFilters,
} from "../discoverFilters";

describe("mature filter and the saved preference", () => {
  it("falls back to the saved preference when the URL says nothing", () => {
    expect(parseDiscoverFilters(new URLSearchParams(), true).isMatureIncluded).toBe(true);
    expect(parseDiscoverFilters(new URLSearchParams(), false).isMatureIncluded).toBe(false);
  });

  it("lets an explicit URL value override the saved preference either way", () => {
    expect(
      parseDiscoverFilters(new URLSearchParams("mature=false"), true).isMatureIncluded,
    ).toBe(false);
    expect(
      parseDiscoverFilters(new URLSearchParams("mature=true"), false).isMatureIncluded,
    ).toBe(true);
  });

  it("writes mature=false only when the saved preference is on and the filter is off", () => {
    const off = { ...parseDiscoverFilters(new URLSearchParams(), false) };

    expect(serializeDiscoverFilters(off, true).get("mature")).toBe("false");
    expect(serializeDiscoverFilters(off, false).has("mature")).toBe(false);
  });

  it("writes mature=true whenever the filter is on", () => {
    const on = { ...parseDiscoverFilters(new URLSearchParams("mature=true")) };

    expect(serializeDiscoverFilters(on, false).get("mature")).toBe("true");
    expect(serializeDiscoverFilters(on, true).get("mature")).toBe("true");
  });

  it("round-trips through the URL without changing the meaning", () => {
    const original = parseDiscoverFilters(new URLSearchParams("mature=false"), true);

    const reparsed = parseDiscoverFilters(serializeDiscoverFilters(original, true), true);

    expect(reparsed.isMatureIncluded).toBe(false);
  });
});
