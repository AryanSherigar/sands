import { describe, it, expect } from "vitest";
import { GENRE_COLORS, GENRE_COLORS_LIGHT } from "../genres";
import { getGenreAccentClass } from "../genreAccent.constants";

describe("Quiet Cinematic Genre Accents", () => {
  it("maps 10 muted genre colors adhering to Quiet Cinematic palette", () => {
    expect(GENRE_COLORS["High Fantasy"]).toBe("#CDBB8E");
    expect(GENRE_COLORS["Sci-Fi"]).toBe("#7FB8C9");
    expect(GENRE_COLORS["Adventure/Survival"]).toBe("#8FB27A");
    expect(GENRE_COLORS["Slice of Life"]).toBe("#D29BB2");
    expect(GENRE_COLORS["Noir / Detective"]).toBe("#C79A74");
    expect(GENRE_COLORS["Post-Apocalyptic/Dystopian"]).toBe("#AFAE8C");
    expect(GENRE_COLORS["Cyberpunk"]).toBe("#C58BC9");
    expect(GENRE_COLORS["Horror"]).toBe("#D0777C");
    expect(GENRE_COLORS["Historical Fiction"]).toBe("#BFA38A");
    expect(GENRE_COLORS["Mystery"]).toBe("#8E9BDB");
  });

  it("defines high-contrast light genre accents matching DESIGN.md", () => {
    expect(GENRE_COLORS_LIGHT["High Fantasy"]).toBe("#7A6431");
    expect(GENRE_COLORS_LIGHT["Sci-Fi"]).toBe("#2F6778");
    expect(GENRE_COLORS_LIGHT["Adventure/Survival"]).toBe("#4A6B38");
    expect(GENRE_COLORS_LIGHT["Slice of Life"]).toBe("#8A4A66");
    expect(GENRE_COLORS_LIGHT["Noir / Detective"]).toBe("#7E5332");
    expect(GENRE_COLORS_LIGHT["Post-Apocalyptic/Dystopian"]).toBe("#5F5E3F");
    expect(GENRE_COLORS_LIGHT["Cyberpunk"]).toBe("#7A4280");
    expect(GENRE_COLORS_LIGHT["Horror"]).toBe("#8E3239");
    expect(GENRE_COLORS_LIGHT["Historical Fiction"]).toBe("#6F5540");
    expect(GENRE_COLORS_LIGHT["Mystery"]).toBe("#44509A");
  });

  it("returns neutral fallback when genre is null or unknown", () => {
    expect(getGenreAccentClass(null)).toBe("[--accent:237_237_239]");
  });
});
