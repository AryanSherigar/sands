import { describe, expect, it } from "vitest";
import { findLevelProblem, nextLevelThreshold, toLevelRows, toValidTiers } from "./levels";

describe("levels", () => {
  it("accepts descending thresholds with one open level and sorts them", () => {
    const rows = toLevelRows([{ name: "Low" }, { name: "High", min: 7 }, { name: "Mid", min: 4 }]);
    expect(findLevelProblem(rows)).toBeNull();
    expect(toValidTiers(rows)).toEqual([{ name: "High", min: 7 }, { name: "Mid", min: 4 }, { name: "Low" }]);
  });

  it("rejects duplicate thresholds and more than one open level", () => {
    expect(toValidTiers(toLevelRows([{ name: "A", min: 3 }, { name: "B", min: 3 }]))).toBeNull();
    expect(toValidTiers(toLevelRows([{ name: "A" }, { name: "B" }]))).toBeNull();
  });

  it("picks a threshold below every existing one", () => {
    expect(nextLevelThreshold(toLevelRows([{ name: "A", min: 7 }, { name: "B", min: 4 }]))).toBe(3);
    expect(nextLevelThreshold(toLevelRows([{ name: "A" }]))).toBe(0);
  });
});
