import { CARD_KIND_ENTITY_TYPE } from "../constants/cardKinds";
import type { CardKind } from "../types/card.types";

const ENTITY_TYPE_TO_CARD_KIND: Record<string, CardKind> = {
  [CARD_KIND_ENTITY_TYPE.character]: "character",
  [CARD_KIND_ENTITY_TYPE.place]: "place",
  [CARD_KIND_ENTITY_TYPE.group]: "group",
  [CARD_KIND_ENTITY_TYPE.thing]: "thing",
  organization: "group",
};

export const getCardKind = (entityType: string): CardKind =>
  ENTITY_TYPE_TO_CARD_KIND[entityType] ?? "other";

export const getEntityTypeForKind = (
  kind: Exclude<CardKind, "other">,
): string => CARD_KIND_ENTITY_TYPE[kind];
