import type { LoreDocument } from "../types/lore.types";

export const textToLore = (text: string): LoreDocument => ({
  blocks: text.trim() ? [{ kind: "text", text }] : [],
});

export const loreToText = (document: LoreDocument): string =>
  document.blocks
    .map((block) => block.text.trim())
    .filter(Boolean)
    .join("\n\n");
