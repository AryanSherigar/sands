import { describe, expect, it } from "vitest";
import { hasPlayerNameToken, insertPlayerNameToken, splitOnPlayerName } from "./openingToken";

describe("openingToken", () => {
  it("starts the box with the token when it is empty", () => {
    expect(insertPlayerNameToken({ blocks: [] }).blocks).toEqual([
      { kind: "text", text: "{player_name}" },
    ]);
  });

  it("appends the token to the leading text with a space", () => {
    const next = insertPlayerNameToken({ blocks: [{ kind: "text", text: "Rain falls on" }] });
    expect(next.blocks[0].text).toBe("Rain falls on {player_name}");
  });

  it("does not add a second space after trailing whitespace", () => {
    const next = insertPlayerNameToken({ blocks: [{ kind: "text", text: "Hello " }] });
    expect(next.blocks[0].text).toBe("Hello {player_name}");
  });

  it("puts a new text block first when the box only has linked blocks", () => {
    const next = insertPlayerNameToken({
      blocks: [{ kind: "answer", question_id: "opening-where", label: "Where", text: "A pier" }],
    });
    expect(next.blocks[0]).toEqual({ kind: "text", text: "{player_name}" });
    expect(next.blocks).toHaveLength(2);
  });

  it("splits text so the token can be shown as a chip", () => {
    expect(splitOnPlayerName("Welcome, {player_name}. Sit.")).toEqual([
      { text: "Welcome, ", isPlayerName: false },
      { text: "{player_name}", isPlayerName: true },
      { text: ". Sit.", isPlayerName: false },
    ]);
  });

  it("detects the token in any block", () => {
    expect(
      hasPlayerNameToken({
        blocks: [
          { kind: "text", text: "x" },
          { kind: "answer", text: "hi {player_name}" },
        ],
      }),
    ).toBe(true);
    expect(hasPlayerNameToken({ blocks: [{ kind: "text", text: "x" }] })).toBe(false);
  });
});
