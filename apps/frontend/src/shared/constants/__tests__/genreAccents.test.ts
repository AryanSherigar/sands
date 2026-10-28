import { describe, it, expect } from "vitest";
import { GENRE_COLORS } from "../genres";
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

  it("returns neutral fallback when genre is null or unknown", () => {
    expect(getGenreAccentClass(null)).toBe("[--accent:237_237_239]");
  });
});
