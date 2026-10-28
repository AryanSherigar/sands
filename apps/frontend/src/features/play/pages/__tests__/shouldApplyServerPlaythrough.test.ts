import { describe, it, expect } from "vitest";
import { shouldApplyServerPlaythrough } from "../shouldApplyServerPlaythrough";

const turns = (count: number) => Array.from({ length: count }, () => ({}));

describe("shouldApplyServerPlaythrough", () => {
  it("applies the first playthrough loaded", () => {
    expect(
      shouldApplyServerPlaythrough(null, { playthrough_id: "a", turns: turns(0) }),
    ).toBe(true);
  });

  it("applies a different playthrough even when it has fewer turns", () => {
    const finished = { playthrough_id: "old", turns: turns(21) };
    const fresh = { playthrough_id: "new", turns: turns(0) };

    expect(shouldApplyServerPlaythrough(finished, fresh)).toBe(true);
  });

  it("ignores a stale refetch of the same playthrough with fewer turns", () => {
    const committed = { playthrough_id: "a", turns: turns(5) };
    const stale = { playthrough_id: "a", turns: turns(4) };

    expect(shouldApplyServerPlaythrough(committed, stale)).toBe(false);
  });

  it("applies a refetch of the same playthrough with as many or more turns", () => {
    const committed = { playthrough_id: "a", turns: turns(5) };

    expect(
      shouldApplyServerPlaythrough(committed, { playthrough_id: "a", turns: turns(5) }),
    ).toBe(true);
    expect(
      shouldApplyServerPlaythrough(committed, { playthrough_id: "a", turns: turns(6) }),
    ).toBe(true);
  });
});
