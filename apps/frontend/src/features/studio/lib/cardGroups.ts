import type { CardKind } from "../types/card.types";
import type { EntityResponse } from "../types/entity.types";
import { getCardKind } from "./cardKind";

export interface GroupedCards {
  player: EntityResponse | null;
  characters: EntityResponse[];
  places: EntityResponse[];
  groups: EntityResponse[];
  things: EntityResponse[];
  others: EntityResponse[];
}

const BUCKET_BY_KIND: Record<CardKind, keyof Omit<GroupedCards, "player">> = {
  character: "characters",
  place: "places",
  group: "groups",
  thing: "things",
  other: "others",
};

export const groupCards = (entities: EntityResponse[]): GroupedCards => {
  const grouped: GroupedCards = {
    player: null,
    characters: [],
    places: [],
    groups: [],
    things: [],
    others: [],
  };
  entities.forEach((entity) => {
    if (entity.is_player) {
      grouped.player = grouped.player ?? entity;
      return;
    }
    grouped[BUCKET_BY_KIND[getCardKind(entity.entity_type)]].push(entity);
  });
  return grouped;
};

export const filterByName = (
  entities: EntityResponse[],
  filterText: string,
): EntityResponse[] => {
  const needle = filterText.trim().toLowerCase();
  if (!needle) return entities;
  return entities.filter((entity) =>
    entity.canonical_name.toLowerCase().includes(needle),
  );
};
