import { PLAYER_NAME_TOKEN } from "../constants/opening";
import type { LoreDocument } from "../types/lore.types";
import { editBlock, prependTextBlock } from "./loreDocument";

export interface TextSegment {
  text: string;
  isPlayerName: boolean;
}

const needsSeparator = (text: string): boolean => text.length > 0 && !/\s$/.test(text);

export const insertPlayerNameToken = (document: LoreDocument): LoreDocument => {
  const leading = document.blocks[0];
  if (!leading || leading.kind !== "text") {
    return prependTextBlock(document, PLAYER_NAME_TOKEN);
  }
  const separator = needsSeparator(leading.text) ? " " : "";
  return editBlock(document, 0, `${leading.text}${separator}${PLAYER_NAME_TOKEN}`);
};

export const splitOnPlayerName = (text: string): TextSegment[] =>
  text
    .split(PLAYER_NAME_TOKEN)
    .flatMap((part, index, parts): TextSegment[] => {
      const segments: TextSegment[] = part ? [{ text: part, isPlayerName: false }] : [];
      if (index < parts.length - 1) segments.push({ text: PLAYER_NAME_TOKEN, isPlayerName: true });
      return segments;
    });

export const hasPlayerNameToken = (document: LoreDocument): boolean =>
  document.blocks.some((block) => block.text.includes(PLAYER_NAME_TOKEN));
