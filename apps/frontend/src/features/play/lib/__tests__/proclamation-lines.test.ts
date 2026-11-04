import { describe, it, expect } from "vitest";
import { parseCouncilReply } from "../proclamation-lines";

describe("parseCouncilReply", () => {
  it("splits every minister into their own line", () => {
    const raw =
      "[CHANCELLOR]: The barons object. [MARSHAL]: The border burns. [TREASURER]: Who pays?";
    expect(parseCouncilReply(raw)).toEqual([
      { speaker: "CHANCELLOR", text: "The barons object." },
      { speaker: "MARSHAL", text: "The border burns." },
      { speaker: "TREASURER", text: "Who pays?" },
    ]);
  });

  it("splits tags that sit in the middle of a chunk of text", () => {
    const raw = "[PRELATE]: Moderation, sire.\n[CHANCELLOR]: Agreed.";
    expect(parseCouncilReply(raw)).toEqual([
      { speaker: "PRELATE", text: "Moderation, sire." },
      { speaker: "CHANCELLOR", text: "Agreed." },
    ]);
  });

  it("holds back a speaker tag that has not finished streaming", () => {
    expect(parseCouncilReply("[CHANCELLOR]: Aye. [MARS")).toEqual([
      { speaker: "CHANCELLOR", text: "Aye." },
    ]);
    expect(parseCouncilReply("[CHANCELLOR]: Aye. [MARSHAL]")).toEqual([
      { speaker: "CHANCELLOR", text: "Aye." },
    ]);
  });

  it("completes a tag that arrived split across two chunks", () => {
    const first = "[CHANCELLOR]: Aye. [MARS";
    const second = `${first}HAL]: Nay.`;
    expect(parseCouncilReply(second)).toEqual([
      { speaker: "CHANCELLOR", text: "Aye." },
      { speaker: "MARSHAL", text: "Nay." },
    ]);
  });

  it("attributes leading untagged text to the council", () => {
    expect(parseCouncilReply("Silence falls. [MARSHAL]: Sire.")).toEqual([
      { speaker: "COUNCIL", text: "Silence falls." },
      { speaker: "MARSHAL", text: "Sire." },
    ]);
  });

  it("returns nothing for an empty reply", () => {
    expect(parseCouncilReply("")).toEqual([]);
  });
});
