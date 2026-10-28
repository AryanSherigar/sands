import {
  OPENING_DOCUMENT_KEY,
} from "../constants/opening";
import { LOGLINE_MAX_LENGTH, TITLE_MAX_LENGTH } from "../constants/guideLimits";
import { SCOPED_APPEND_SEPARATOR } from "../constants/scopedChat";
import {
  PREMISE_DOCUMENT_KEY,
  WORLD_LORE_DOCUMENT_KEY,
} from "../constants/worldDocumentKeys";
import type { EntityResponse, EntityUpdate } from "../types/entity.types";
import type { LoreDocument } from "../types/lore.types";
import type { ScenarioResponse } from "../types/scenario.types";
import type { ScenarioFieldsPatch } from "../types/scenarioPatch.types";
import type { ScopedSlotId, ScopedWriteMode } from "../types/scopedChat.types";
import { EMPTY_LORE_DOCUMENT, readWorldDocument } from "./worldDocuments";

export interface SlotSource {
  scenario: ScenarioResponse | null;
  entity: EntityResponse | null;
}

export interface SlotWrite {
  scenarioPatch: ScenarioFieldsPatch | null;
  entityUpdate: EntityUpdate | null;
}

const WORLD_DOCUMENT_KEYS: Partial<Record<ScopedSlotId, string>> = {
  premise: PREMISE_DOCUMENT_KEY,
  world_lore: WORLD_LORE_DOCUMENT_KEY,
  opening: OPENING_DOCUMENT_KEY,
};

export const getFreeText = (document: LoreDocument): string =>
  document.blocks
    .filter((block) => block.kind === "text")
    .map((block) => block.text.trim())
    .filter((text) => text.length > 0)
    .join(SCOPED_APPEND_SEPARATOR);

export const setFreeText = (document: LoreDocument, text: string): LoreDocument => {
  const linkedBlocks = document.blocks.filter((block) => block.kind !== "text");
  const trimmed = text.trim();
  if (trimmed.length === 0) return { blocks: linkedBlocks };
  return { blocks: [{ kind: "text", text: trimmed }, ...linkedBlocks] };
};

export const combineText = (
  existing: string,
  proposed: string,
  mode: ScopedWriteMode,
): string => {
  if (mode === "replace" || existing.trim().length === 0) return proposed;
  return `${existing}${SCOPED_APPEND_SEPARATOR}${proposed}`;
};

const readDocument = (slot: ScopedSlotId, source: SlotSource): LoreDocument => {
  if (slot === "style") {
    return source.scenario?.narrator_persona_document ?? EMPTY_LORE_DOCUMENT;
  }
  if (slot === "card_lore") return source.entity?.lore_document ?? EMPTY_LORE_DOCUMENT;
  const key = WORLD_DOCUMENT_KEYS[slot];
  return key ? readWorldDocument(source.scenario?.world_data, key) : EMPTY_LORE_DOCUMENT;
};

export const readSlotText = (slot: ScopedSlotId, source: SlotSource): string => {
  if (slot === "title") return source.scenario?.title ?? "";
  if (slot === "logline") return source.scenario?.logline ?? "";
  return getFreeText(readDocument(slot, source));
};

export const buildSlotWrite = (
  slot: ScopedSlotId,
  source: SlotSource,
  text: string,
): SlotWrite => {
  if (slot === "title") {
    return { scenarioPatch: { title: text.slice(0, TITLE_MAX_LENGTH) }, entityUpdate: null };
  }
  if (slot === "logline") {
    return { scenarioPatch: { logline: text.slice(0, LOGLINE_MAX_LENGTH) }, entityUpdate: null };
  }
  const next = setFreeText(readDocument(slot, source), text);
  if (slot === "card_lore") {
    return { scenarioPatch: null, entityUpdate: { lore_document: next } };
  }
  if (slot === "style") {
    return { scenarioPatch: { narrator_persona_document: next }, entityUpdate: null };
  }
  const key = WORLD_DOCUMENT_KEYS[slot] as string;
  return { scenarioPatch: { worldData: { [key]: next } }, entityUpdate: null };
};
