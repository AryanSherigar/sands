import { LORE_BOX_MAX_ROWS, LORE_BOX_MIN_ROWS } from "../constants/loreBox";

export const getTextareaRows = (text: string): number => {
  const lineCount = text.split("\n").length;
  return Math.min(LORE_BOX_MAX_ROWS, Math.max(LORE_BOX_MIN_ROWS, lineCount));
};
