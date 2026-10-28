import { useCallback, useEffect, useRef } from "react";
import { useToast } from "@/shared/hooks/useToast";
import { logEvent } from "@/shared/lib/logger";
import { CARD_VALUE_SAVE_FAILED_MESSAGE } from "../constants/cardValues";
import { buildCardValueKey, buildNewCardValue, type CardValueKind } from "../lib/cardValues";
import type { AttributeFieldSchema, EntityResponse } from "../types/entity.types";
import { useEntities } from "./useEntities";
import { useRowAutosave } from "./useRowAutosave";

type Attributes = Record<string, AttributeFieldSchema>;
const NO_ATTRIBUTES: Attributes = {};

export const useCardValues = (scenarioId: string, entity: EntityResponse) => {
  const { updateEntityAsync } = useEntities(scenarioId);
  const showToast = useToast();
  const { entity_id: entityId } = entity;

  const save = useCallback(
    (attributes: Attributes): void => {
      updateEntityAsync({ entityId, payload: { attributes_schema: attributes } }).catch((error) => {
        logEvent("warning", "card_values_save_failed", { error: String(error) });
        showToast(CARD_VALUE_SAVE_FAILED_MESSAGE, "error");
      });
    },
    [entityId, showToast, updateEntityAsync],
  );
  const { value: attributes, commit } = useRowAutosave<Attributes>({
    serverDraft: entity.attributes_schema ?? NO_ATTRIBUTES,
    save,
  });
  const attributesRef = useRef(attributes);
  useEffect(() => {
    attributesRef.current = attributes;
  });

  const writeValue = useCallback(
    (key: string, next: AttributeFieldSchema): void => commit({ ...attributesRef.current, [key]: next }),
    [commit],
  );
  const addValue = useCallback(
    (name: string, kind: CardValueKind): void => {
      const key = buildCardValueKey(name, attributesRef.current);
      commit({ ...attributesRef.current, [key]: buildNewCardValue(name, kind) });
    },
    [commit],
  );
  const removeValue = useCallback(
    (key: string): void => {
      const { [key]: _removed, ...rest } = attributesRef.current;
      commit(rest);
    },
    [commit],
  );

  return { attributes, writeValue, addValue, removeValue };
};
