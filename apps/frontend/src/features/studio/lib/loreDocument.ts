import { moveItem } from "@/shared/lib/moveItem";
import type { GuideQuestion } from "../types/guide.types";
import type { LoreBlock, LoreDocument } from "../types/lore.types";

export type AnswerQuestion = Pick<GuideQuestion, "id" | "label">;

const isBlank = (text: string): boolean => text.trim().length === 0;

const findAnswerIndex = (document: LoreDocument, questionId: string): number =>
  document.blocks.findIndex(
    (block) => block.kind === "answer" && block.question_id === questionId,
  );

const withBlocks = (blocks: LoreBlock[]): LoreDocument => ({ blocks });

const buildAnswerBlock = (question: AnswerQuestion, text: string): LoreBlock => ({
  kind: "answer",
  question_id: question.id,
  label: question.label,
  text,
});

export const getAnswer = (document: LoreDocument, questionId: string): string => {
  const index = findAnswerIndex(document, questionId);
  return index === -1 ? "" : document.blocks[index].text;
};

export const addAnswerBlock = (
  document: LoreDocument,
  question: AnswerQuestion,
  text: string,
): LoreDocument =>
  withBlocks([...document.blocks, buildAnswerBlock(question, text)]);

export const prependTextBlock = (
  document: LoreDocument,
  text: string,
): LoreDocument => withBlocks([{ kind: "text", text }, ...document.blocks]);

export const editBlock = (
  document: LoreDocument,
  index: number,
  text: string,
): LoreDocument =>
  withBlocks(
    document.blocks.map((block, blockIndex) =>
      blockIndex === index ? { ...block, text } : block,
    ),
  );

export const removeBlock = (
  document: LoreDocument,
  index: number,
): LoreDocument =>
  withBlocks(document.blocks.filter((_, blockIndex) => blockIndex !== index));

export const setAnswer = (
  document: LoreDocument,
  question: AnswerQuestion,
  text: string,
): LoreDocument => {
  const index = findAnswerIndex(document, question.id);
  if (index === -1) {
    return isBlank(text) ? document : addAnswerBlock(document, question, text);
  }
  return isBlank(text) ? removeBlock(document, index) : editBlock(document, index, text);
};

export const unlinkBlock = (
  document: LoreDocument,
  index: number,
): LoreDocument =>
  withBlocks(
    document.blocks.map((block, blockIndex) =>
      blockIndex === index ? { kind: "text", text: block.text } : block,
    ),
  );

export const reorderBlocks = (
  document: LoreDocument,
  fromIndex: number,
  toIndex: number,
): LoreDocument => withBlocks(moveItem(document.blocks, fromIndex, toIndex));

export const countAnsweredQuestions = (
  document: LoreDocument,
  questionIds: readonly string[],
): number =>
  questionIds.filter((questionId) => !isBlank(getAnswer(document, questionId)))
    .length;

export const countWords = (document: LoreDocument): number =>
  document.blocks
    .flatMap((block) => block.text.split(/\s+/))
    .filter((word) => word.length > 0).length;

export const renderBlockLine = (block: LoreBlock): string => {
  const text = block.text.trim();
  if (block.kind === "answer" && block.label) return `${block.label}: ${text}`;
  return text;
};
