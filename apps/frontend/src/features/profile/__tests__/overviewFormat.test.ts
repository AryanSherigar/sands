import { describe, expect, it } from "vitest";
import {
  formatContinueSubtitle,
  formatEndingsCompletion,
  formatGenresSubtext,
  formatRelativeTime,
} from "../lib/overviewFormat";
import { getGenreAccentClass } from "@/shared/constants/genreAccent.constants";

const NOW = new Date("2026-11-05T12:00:00Z");

describe("formatGenresSubtext", () => {
  it("shows up to three genres and a +N remainder", () => {
    expect(
      formatGenresSubtext([
        "Noir / Detective",
        "Sci-Fi",
        "High Fantasy",
        "Horror",
        "Mystery",
      ]),
    ).toBe("Noir / Detective, Sci-Fi, High Fantasy +2");
    expect(formatGenresSubtext(["Sci-Fi", "Horror"])).toBe("Sci-Fi, Horror");
  });

  it("has a neutral empty message", () => {
    expect(formatGenresSubtext([])).toBe("None yet");
  });
});

describe("formatRelativeTime", () => {
  it.each([
    ["2026-11-05T11:59:40Z", "just now"],
    ["2026-11-05T11:55:00Z", "5m ago"],
    ["2026-11-05T10:00:00Z", "2h ago"],
    ["2026-11-04T09:00:00Z", "yesterday"],
    ["2026-11-02T12:00:00Z", "3d ago"],
  ])("%s -> %s", (iso, expected) => {
    expect(formatRelativeTime(iso, NOW)).toBe(expected);
  });

  it("falls back to a date after a week and clamps future timestamps", () => {
    expect(formatRelativeTime("2026-10-27T12:00:00Z", NOW)).toMatch(/2026/);
    expect(formatRelativeTime("2026-11-05T12:05:00Z", NOW)).toBe("just now");
  });
});

describe("formatContinueSubtitle", () => {
  it("joins genre and mode in upper case", () => {
    expect(formatContinueSubtitle("Noir / Detective", "master")).toBe(
      "NOIR / DETECTIVE · MASTER MODE",
    );
  });

  it("omits a missing genre", () => {
    expect(formatContinueSubtitle(null, "newbie")).toBe("NEWBIE MODE");
  });
});

describe("getGenreAccentClass", () => {
  it("maps known genres to a static accent-scoping class", () => {
    expect(getGenreAccentClass("Noir / Detective")).toContain("[--accent:");
  });

  it("falls back to the neutral muted accent for unknown or missing genres", () => {
    expect(getGenreAccentClass("Space Opera")).toContain("237_237_239");
    expect(getGenreAccentClass(null)).toContain("237_237_239");
  });
});

describe("formatEndingsCompletion", () => {
  it("formats a percentage with one decimal place", () => {
    expect(formatEndingsCompletion(14, 32)).toBe("43.8% completion");
    expect(formatEndingsCompletion(0, 5)).toBe("0.0% completion");
    expect(formatEndingsCompletion(5, 5)).toBe("100.0% completion");
  });

  it("never divides by zero", () => {
    expect(formatEndingsCompletion(0, 0)).toBe("No endings yet");
  });
});
