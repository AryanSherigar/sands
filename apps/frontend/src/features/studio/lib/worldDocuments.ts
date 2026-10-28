import type { LoreDocument } from "../types/lore.types";

export const EMPTY_LORE_DOCUMENT: LoreDocument = { blocks: [] };

const isLoreDocument = (value: unknown): value is LoreDocument =>
  typeof value === "object" &&
  value !== null &&
  Array.isArray((value as LoreDocument).blocks);

export const readWorldDocument = (
  worldData: Record<string, unknown> | undefined,
  key: string,
): LoreDocument => {
  const stored = worldData?.[key];
  return isLoreDocument(stored) ? stored : EMPTY_LORE_DOCUMENT;
};
