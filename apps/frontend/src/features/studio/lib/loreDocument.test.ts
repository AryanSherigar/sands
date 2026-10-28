import { describe, expect, it } from "vitest";
import {
  addAnswerBlock,
  countAnsweredQuestions,
  countWords,
  editBlock,
  getAnswer,
  prependTextBlock,
  removeBlock,
  reorderBlocks,
  setAnswer,
  unlinkBlock,
} from "./loreDocument";
import type { LoreDocument } from "../types/lore.types";

const VOICE = { id: "voice", label: "Voice" };
const LOOKS = { id: "looks", label: "Looks" };

const emptyDocument: LoreDocument = { blocks: [] };

describe("loreDocument reducers", () => {
  it("addAnswerBlock appends a labelled answer block", () => {
    const next = addAnswerBlock(emptyDocument, VOICE, "Slow and low.");

    expect(next.blocks).toEqual([
      { kind: "answer", question_id: "voice", label: "Voice", text: "Slow and low." },
    ]);
    expect(emptyDocument.blocks).toHaveLength(0);
  });

  it("setAnswer creates, updates and removes the linked block", () => {
    const created = setAnswer(emptyDocument, VOICE, "Slow");
    const updated = setAnswer(created, VOICE, "Slow and low");
    const cleared = setAnswer(updated, VOICE, "   ");

    expect(created.blocks).toHaveLength(1);
    expect(getAnswer(updated, "voice")).toBe("Slow and low");
    expect(updated.blocks).toHaveLength(1);
    expect(cleared.blocks).toHaveLength(0);
  });

  it("setAnswer with no text never creates a block", () => {
    expect(setAnswer(emptyDocument, VOICE, "").blocks).toHaveLength(0);
  });

  it("editBlock changes only the targeted block text", () => {
    const start = setAnswer(
      prependTextBlock(emptyDocument, "Free words."),
      VOICE,
      "Slow",
    );

    const next = editBlock(start, 1, "Slow and low");

    expect(next.blocks[0].text).toBe("Free words.");
    expect(getAnswer(next, "voice")).toBe("Slow and low");
  });

  it("removeBlock clears the answer", () => {
    const start = setAnswer(emptyDocument, VOICE, "Slow");

    const next = removeBlock(start, 0);

    expect(getAnswer(next, "voice")).toBe("");
    expect(next.blocks).toHaveLength(0);
  });

  it("unlinkBlock keeps the words as plain text and empties the answer", () => {
    const start = setAnswer(emptyDocument, VOICE, "Slow and low");

    const next = unlinkBlock(start, 0);

    expect(next.blocks).toEqual([{ kind: "text", text: "Slow and low" }]);
    expect(getAnswer(next, "voice")).toBe("");
  });

  it("reorderBlocks moves a block without mutating the input", () => {
    const start = setAnswer(setAnswer(emptyDocument, VOICE, "a"), LOOKS, "b");

    const next = reorderBlocks(start, 1, 0);

    expect(next.blocks.map((block) => block.question_id)).toEqual([
      "looks",
      "voice",
    ]);
    expect(start.blocks[0].question_id).toBe("voice");
  });

  it("countAnsweredQuestions ignores empty answers", () => {
    const start = setAnswer(emptyDocument, VOICE, "a");
    const withEmpty = editBlock(
      addAnswerBlock(start, LOOKS, "x"),
      1,
      "",
    );

    expect(countAnsweredQuestions(withEmpty, ["voice", "looks", "wants"])).toBe(1);
  });

  it("countWords counts words across every block", () => {
    const start = setAnswer(prependTextBlock(emptyDocument, "One two"), VOICE, "three");

    expect(countWords(start)).toBe(3);
  });
});
