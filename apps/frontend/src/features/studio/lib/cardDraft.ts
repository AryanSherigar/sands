import { CARD_KIND_LABELS } from "../constants/cardKinds";
import type { CardKind } from "../types/card.types";
import type { EntityCreate, EntityResponse, EntityUpdate } from "../types/entity.types";
import type { LoreDocument } from "../types/lore.types";
import { getEntityTypeForKind } from "./cardKind";

export interface CardDraft {
  name: string;
  aliases: string[];
  lore: LoreDocument;
}

export interface NewCardRequest {
  kind: CardKind;
  name?: string;
  entityType?: string;
  isPlayer?: boolean;
}

const isSameTrigger = (first: string, second: string): boolean =>
  first.trim().toLowerCase() === second.trim().toLowerCase();

export const buildCardDraft = (entity: EntityResponse): CardDraft => {
  const description = entity.description?.trim() ?? "";
  const fallbackLore: LoreDocument = {
    blocks: description ? [{ kind: "text", text: description }] : [],
  };
  return {
    name: entity.canonical_name,
    aliases: entity.aliases,
    lore: entity.lore_document ?? fallbackLore,
  };
};

export const buildEntityUpdate = (draft: CardDraft): EntityUpdate => ({
  canonical_name: draft.name,
  aliases: draft.aliases,
  lore_document: draft.lore,
});

export const renameTrigger = (
  aliases: string[],
  previousName: string,
  nextName: string,
): string[] => {
  const index = aliases.findIndex((alias) => isSameTrigger(alias, previousName));
  if (index === -1) return aliases;
  return aliases.map((alias, aliasIndex) =>
    aliasIndex === index ? nextName : alias,
  );
};

export const addTrigger = (aliases: string[], trigger: string): string[] => {
  const cleaned = trigger.trim();
  if (!cleaned || aliases.some((alias) => isSameTrigger(alias, cleaned))) {
    return aliases;
  }
  return [...aliases, cleaned];
};

export const removeTrigger = (aliases: string[], trigger: string): string[] =>
  aliases.filter((alias) => alias !== trigger);

export const buildNewCardPayload = ({
  kind,
  name,
  entityType,
  isPlayer,
}: NewCardRequest): EntityCreate => {
  const cardName =
    name?.trim() || `New ${CARD_KIND_LABELS[kind].toLowerCase()}`;
  const resolvedType =
    kind === "other" ? (entityType ?? "other") : getEntityTypeForKind(kind);
  return {
    entity_type: resolvedType,
    canonical_name: cardName,
    aliases: [cardName],
    lore_document: { blocks: [] },
    ...(isPlayer ? { is_player: true } : {}),
  };
};

export const buildDuplicatePayload = (entity: EntityResponse): EntityCreate => {
  const copyName = `${entity.canonical_name} copy`;
  return {
    entity_type: entity.entity_type,
    canonical_name: copyName,
    aliases: renameTrigger(entity.aliases, entity.canonical_name, copyName),
    lore_document: buildCardDraft(entity).lore,
  };
};
