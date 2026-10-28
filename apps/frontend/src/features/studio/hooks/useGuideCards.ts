import { useMemo } from "react";
import { groupCards } from "../lib/cardGroups";
import { getCardKind } from "../lib/cardKind";
import type { EntityResponse } from "../types/entity.types";
import { useEntities } from "./useEntities";
import { useGuide } from "./useGuide";
import { useScenarioEntityTypes } from "./useScenarioEntityTypes";

const PLAYER_TYPE_LABEL = "Player";

export const useGuideCards = () => {
  const { scenarioId } = useGuide();
  const { entities, isLoading } = useEntities(scenarioId);
  const { entityTypes } = useScenarioEntityTypes(scenarioId);
  const cards = useMemo(() => groupCards(entities), [entities]);

  const getTypeLabel = (entity: EntityResponse): string | undefined => {
    if (entity.is_player) return PLAYER_TYPE_LABEL;
    if (getCardKind(entity.entity_type) !== "other") return undefined;
    return entityTypes.find((type) => type.type_key === entity.entity_type)?.display_label;
  };

  return { entities, cards, isLoading, getTypeLabel };
};
