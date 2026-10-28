import { describe, expect, it } from "vitest";
import { formatClock } from "./formatClock";

describe("formatClock", () => {
  it("shows the start time at zero minutes", () => {
    expect(formatClock(0, "23:00", "24h")).toBe("23:00");
    expect(formatClock(0, "23:00", "12h")).toBe("11:00 PM");
  });

  it("adds minutes since the start: 420 minutes from 23:00 is 06:00", () => {
    expect(formatClock(420, "23:00", "24h")).toBe("06:00");
    expect(formatClock(420, "23:00", "12h")).toBe("06:00 AM");
  });

  it("wraps past midnight", () => {
    expect(formatClock(60, "23:30", "24h")).toBe("00:30");
    expect(formatClock(60, "23:30", "12h")).toBe("12:30 AM");
  });

  it("shows noon and midnight as 12", () => {
    expect(formatClock(0, "12:00", "12h")).toBe("12:00 PM");
    expect(formatClock(0, "00:00", "12h")).toBe("12:00 AM");
  });

  it("pads minutes and hours", () => {
    expect(formatClock(5, "03:00", "12h")).toBe("03:05 AM");
  });

  it("wraps across more than a day", () => {
    expect(formatClock(1500, "23:00", "24h")).toBe("00:00");
  });

  it("floors fractional minutes", () => {
    expect(formatClock(59.9, "00:00", "24h")).toBe("00:59");
  });

  it("treats a negative offset as before the start", () => {
    expect(formatClock(-30, "00:15", "24h")).toBe("23:45");
  });

  it("falls back to midnight for an unreadable start", () => {
    expect(formatClock(0, "noon", "24h")).toBe("00:00");
  });

  it("shows an impossible minute when a glitch minute is given", () => {
    expect(formatClock(180, "23:00", "12h", 84)).toBe("02:84 AM");
    expect(formatClock(180, "23:00", "24h", 61)).toBe("02:61");
  });
});
