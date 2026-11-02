import { describe, expect, it } from "vitest";
import { describeEnding, describeEndingInput } from "../endingText";

describe("describeEnding", () => {
  it("names a known default ending and its grade", () => {
    const description = describeEnding({
      ending_id: "default_graded_end_date",
      kind: "graded",
      turn: 40,
      grade: "pyrrhic",
    });

    expect(description.headline).toBe("The Campaign Ends");
    expect(description.gradeLabel).toBe("Pyrrhic");
  });

  it("falls back to the kind, then to a readable id, for authored endings", () => {
    expect(describeEnding({ ending_id: "x", kind: "victory", turn: 1 }).headline).toBe("Victory");
    expect(describeEnding({ ending_id: "the_long_winter", kind: "other", turn: 1 }).headline).toBe(
      "The Long Winter",
    );
  });

  it("labels grade inputs", () => {
    expect(describeEndingInput("position")).toBe("Land held");
    expect(describeEndingInput("custom_thing")).toBe("Custom Thing");
  });
});
