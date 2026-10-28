import { useCallback } from "react";
import {
  GUIDE_TAB_LABEL,
  MISSING_TAB_LABEL,
  PLAYTEST_TAB_LABEL,
} from "../constants/studioTabs";
import { getExtraByFeatureId } from "../lib/extras";
import { getFeatureById } from "../lib/newFeatures";
import { parseTabId } from "../lib/studioTabs";
import { useGuideCards } from "./useGuideCards";

const FEATURE_TAB_LABEL = "New feature";
const UNNAMED_CARD_LABEL = "Untitled";

export const useTabLabels = () => {
  const { entities, isLoading } = useGuideCards();

  return useCallback(
    (tabId: string): string => {
      const target = parseTabId(tabId);
      if (!target) return MISSING_TAB_LABEL;
      if (target.kind === "guide") return GUIDE_TAB_LABEL;
      if (target.kind === "playtest") return PLAYTEST_TAB_LABEL;
      if (target.kind === "feature") {
        const extra = getExtraByFeatureId(target.targetId ?? "");
        if (extra) return extra.name;
        return getFeatureById(target.targetId ?? "")?.name ?? FEATURE_TAB_LABEL;
      }
      const entity = entities.find((candidate) => candidate.entity_id === target.targetId);
      if (entity) return entity.canonical_name.trim() || UNNAMED_CARD_LABEL;
      return isLoading ? "" : MISSING_TAB_LABEL;
    },
    [entities, isLoading],
  );
};
