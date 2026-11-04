import { describe, expect, it } from "vitest";
import { bookFileName, composeBookText } from "../bookExport";

describe("composeBookText", () => {
  it("puts the cover first, then the chapters in order, then the closing entry", () => {
    const text = composeBookText({
      rulerName: "King Alden IV",
      chroniclerName: "Vaelen the Scorned",
      chroniclerTitle: "Court Historian",
      eraLabel: "Spring 1042 to Winter 1051",
      chapters: ["The first winter was hard.", "The marches rose in spring."],
      closingEntry: "They remember a cruel crown.",
    });

    expect(text).toBe(
      [
        "King Alden IV\nSpring 1042 to Winter 1051\nWritten by Vaelen the Scorned, Court Historian",
        "The first winter was hard.",
        "The marches rose in spring.",
        "They remember a cruel crown.",
      ].join("\n\n"),
    );
  });
});

describe("bookFileName", () => {
  it("makes a safe file name from the ruler", () => {
    expect(bookFileName("King Alden IV")).toBe("king-alden-iv-chronicle.txt");
    expect(bookFileName("***")).toBe("chronicle-chronicle.txt");
  });
});
