import { describe, expect, it } from "vitest";
import { loreToText, textToLore } from "./loreText";

describe("loreText", () => {
  it("turns plain text into one text block and back", () => {
    expect(textToLore("The tide comes in.")).toEqual({
      blocks: [{ kind: "text", text: "The tide comes in." }],
    });
    expect(loreToText(textToLore("The tide comes in."))).toBe("The tide comes in.");
  });

  it("gives an empty document for blank text", () => {
    expect(textToLore("   ").blocks).toEqual([]);
  });

  it("joins text and answer blocks without their labels", () => {
    const text = loreToText({
      blocks: [
        { kind: "text", text: "Dawn breaks." },
        { kind: "answer", question_id: "ending-last-line", label: "The last line", text: "She never looked back." },
      ],
    });
    expect(text).toBe("Dawn breaks.\n\nShe never looked back.");
  });
});
