import { describe, expect, it } from "vitest";
import {
  getNextTabIndex,
  getVisibleTabs,
  resolveProfileTab,
} from "../lib/profileTabs";

describe("getVisibleTabs", () => {
  it("returns all seven tabs in order for the owner", () => {
    expect(getVisibleTabs(true).map((tab) => tab.id)).toEqual([
      "overview",
      "creations",
      "campaigns",
      "endings",
      "achievements",
      "bookmarks",
      "reviews",
    ]);
  });

  it("returns only public tabs for a visitor", () => {
    expect(getVisibleTabs(false).map((tab) => tab.id)).toEqual([
      "creations",
      "achievements",
      "reviews",
    ]);
  });
});

describe("resolveProfileTab", () => {
  it("accepts a permitted tab", () => {
    expect(resolveProfileTab("campaigns", getVisibleTabs(true))).toBe(
      "campaigns",
    );
  });

  it("falls back to creations for an owner-only tab in a visitor view", () => {
    expect(resolveProfileTab("campaigns", getVisibleTabs(false))).toBe(
      "creations",
    );
  });

  it("falls back to overview for the owner on null and unknown values", () => {
    expect(resolveProfileTab(null, getVisibleTabs(true))).toBe("overview");
    expect(resolveProfileTab("nope", getVisibleTabs(true))).toBe("overview");
  });

  it("keeps achievements for a visitor since it is a public tab", () => {
    expect(resolveProfileTab("achievements", getVisibleTabs(false))).toBe(
      "achievements",
    );
  });

  it("falls back to creations for a visitor on owner-only tabs", () => {
    expect(resolveProfileTab("endings", getVisibleTabs(false))).toBe(
      "creations",
    );
  });

  it("falls back to creations for a visitor, including for overview", () => {
    expect(resolveProfileTab(null, getVisibleTabs(false))).toBe("creations");
    expect(resolveProfileTab("overview", getVisibleTabs(false))).toBe(
      "creations",
    );
  });
});

describe("getNextTabIndex", () => {
  it("moves right and wraps", () => {
    expect(getNextTabIndex(0, 4, "ArrowRight")).toBe(1);
    expect(getNextTabIndex(3, 4, "ArrowRight")).toBe(0);
  });

  it("moves left and wraps", () => {
    expect(getNextTabIndex(0, 4, "ArrowLeft")).toBe(3);
  });

  it("jumps with Home and End", () => {
    expect(getNextTabIndex(2, 4, "Home")).toBe(0);
    expect(getNextTabIndex(1, 4, "End")).toBe(3);
  });

  it("returns null for unrelated keys", () => {
    expect(getNextTabIndex(1, 4, "Enter")).toBeNull();
  });
});
