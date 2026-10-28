import { useMemo } from "react";
import {
  addAnswerBlock,
  AnswerQuestion,
  editBlock,
  prependTextBlock,
  removeBlock,
  reorderBlocks,
  setAnswer,
  unlinkBlock,
} from "../lib/loreDocument";
import type { LoreDocument } from "../types/lore.types";

export const useLoreDocument = (
  document: LoreDocument,
  onChange: (next: LoreDocument) => void,
) =>
  useMemo(
    () => ({
      prependText: (text: string) => onChange(prependTextBlock(document, text)),
      editBlock: (index: number, text: string) =>
        onChange(editBlock(document, index, text)),
      setAnswer: (question: AnswerQuestion, text: string) =>
        onChange(setAnswer(document, question, text)),
      addAnswerBlock: (question: AnswerQuestion, text: string) =>
        onChange(addAnswerBlock(document, question, text)),
      removeBlock: (index: number) => onChange(removeBlock(document, index)),
      unlinkBlock: (index: number) => onChange(unlinkBlock(document, index)),
      reorderBlocks: (fromIndex: number, toIndex: number) =>
        onChange(reorderBlocks(document, fromIndex, toIndex)),
    }),
    [document, onChange],
  );
