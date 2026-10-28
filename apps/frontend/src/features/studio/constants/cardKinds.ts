import type { CardKind } from "../types/card.types";

export const CARD_KIND_ENTITY_TYPE: Record<
  Exclude<CardKind, "other">,
  string
> = {
  character: "character",
  place: "location",
  group: "faction",
  thing: "item",
};

export const CARD_KIND_LABELS: Record<CardKind, string> = {
  character: "Character",
  place: "Place",
  group: "Group",
  thing: "Thing",
  other: "Other",
};

export const CARD_KIND_PICK_PLACEHOLDERS: Record<CardKind | "any", string> = {
  character: "Choose a character…",
  place: "Choose a place…",
  group: "Choose a group…",
  thing: "Choose a thing…",
  other: "Choose a card…",
  any: "Choose a card…",
};
