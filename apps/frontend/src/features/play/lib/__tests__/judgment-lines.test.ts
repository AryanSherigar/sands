import { describe, expect, it } from "vitest";
import { parseCourtText } from "../judgment-lines";

describe("parseCourtText", () => {
  it("splits narration from speaker lines", () => {
    const lines = parseCourtText(
      'The hall is silent.\nBRANNOCH: "An open defiance requires an open reckoning."',
    );
    expect(lines).toEqual([
      { kind: "narration", text: "The hall is silent." },
      {
        kind: "speech",
        speaker: "Brannoch",
        text: "An open defiance requires an open reckoning.",
      },
    ]);
  });

  it("accepts curly quotes and multi-word speaker names", () => {
    const [line] = parseCourtText("LORD HARL: “I did what any man would do.”");
    expect(line).toEqual({
      kind: "speech",
      speaker: "Lord Harl",
      text: "I did what any man would do.",
    });
  });

  it("treats a line without a capitalised speaker as narration", () => {
    const lines = parseCourtText("Note: the bells toll.\n\nA draught stirs the banners.");
    expect(lines.map((line) => line.kind)).toEqual(["narration", "narration"]);
  });

  it("drops blank lines and returns nothing for empty text", () => {
    expect(parseCourtText("")).toEqual([]);
    expect(parseCourtText("\n\n  \n")).toEqual([]);
  });

  it("keeps unquoted speech after a speaker tag", () => {
    const [line] = parseCourtText("VEYRA: Spare him, Sire.");
    expect(line).toEqual({ kind: "speech", speaker: "Veyra", text: "Spare him, Sire." });
  });
});
