import { describe, it, expect } from "vitest";
import { deriveDate } from "../strategyClock";

describe("deriveDate", () => {
  it("returns the start date on turn zero", () => {
    expect(deriveDate({ turn: 0, start_year: 1042, start_month: 7 })).toEqual({
      year: 1042,
      month: 7,
      season: "Summer",
    });
  });

  it("advances two months per turn and rolls over the year", () => {
    expect(deriveDate({ turn: 3, start_year: 1042, start_month: 7 })).toEqual({
      year: 1043,
      month: 1,
      season: "Winter",
    });
  });

  it("supports a turn offset for the next season", () => {
    expect(deriveDate({ turn: 1, start_year: 1042, start_month: 7 }, 1)).toEqual({
      year: 1042,
      month: 11,
      season: "Autumn",
    });
  });
});
