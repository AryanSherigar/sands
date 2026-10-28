import { useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";
import { createEntity } from "../api/entities.api";
import {
  createScenarioEntityType,
  listScenarioEntityTypes,
} from "../api/scenario_entity_types.api";
import { runGuardedWrite, withEditStamp } from "../lib/editGuard";
import { buildNewCardPayload } from "../lib/cardDraft";
import { toEntityTypeKey } from "../lib/entityTypeKey";
import type { CardKind } from "../types/card.types";
import type { EntityResponse } from "../types/entity.types";

export interface AddCardOptions {
  name?: string;
  typeName?: string;
  isPlayer?: boolean;
  shouldOpenTab?: boolean;
}

const MAX_TYPE_LABEL_LENGTH = 60;

export const useAddCard = (ensureDraft: () => Promise<string>) => {
  const queryClient = useQueryClient();

  const ensureEntityType = useCallback(
    async (scenarioId: string, typeName: string): Promise<string> => {
      const typeKey = toEntityTypeKey(typeName);
      const existing = await listScenarioEntityTypes(scenarioId);
      if (existing.items.some((item) => item.type_key === typeKey)) return typeKey;
      await runGuardedWrite(
        queryClient,
        scenarioId,
        () =>
          createScenarioEntityType(scenarioId, {
            type_key: typeKey,
            display_label: typeName.trim().slice(0, MAX_TYPE_LABEL_LENGTH),
          }),
        { shouldRefreshStamp: true },
      );
      queryClient.invalidateQueries({ queryKey: ["scenario-entity-types", scenarioId] });
      return typeKey;
    },
    [queryClient],
  );

  return useCallback(
    async (kind: CardKind, options: AddCardOptions = {}): Promise<EntityResponse> => {
      const scenarioId = await ensureDraft();
      const entityType =
        kind === "other" && options.typeName
          ? await ensureEntityType(scenarioId, options.typeName)
          : undefined;
      const payload = buildNewCardPayload({
        kind,
        name: options.name,
        entityType,
        isPlayer: options.isPlayer,
      });
      const created = await runGuardedWrite(queryClient, scenarioId, (stamp) =>
        createEntity(scenarioId, withEditStamp(payload, stamp)),
      );
      queryClient.invalidateQueries({ queryKey: ["entities", scenarioId] });
      return created;
    },
    [ensureDraft, ensureEntityType, queryClient],
  );
};
