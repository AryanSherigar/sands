import { useEffect } from "react";
import { useStudioTabsStore } from "../stores/studioTabs.store";
import { useEntities } from "./useEntities";
import { useGuide } from "./useGuide";

export const usePruneMissingCardTabs = (): void => {
  const { scenarioId } = useGuide();
  const { entities, isLoading, error } = useEntities(scenarioId);

  useEffect(() => {
    if (!scenarioId || isLoading || error) return;
    useStudioTabsStore
      .getState()
      .pruneCardTabs(new Set(entities.map((entity) => entity.entity_id)));
  }, [scenarioId, entities, isLoading, error]);
};
