import { useMemo } from "react";
import {
  addSeenFeature,
  getFeaturesReleasedAfter,
  splitFeaturesBySeen,
} from "../lib/newFeatures";
import { useGuide } from "./useGuide";
import { useSyncedValue } from "./useSyncedValue";

const NO_FEATURE_IDS: string[] = [];

export const useNewFeatures = () => {
  const { scenario, saveFields } = useGuide();
  const createdAt = scenario?.created_at ?? null;
  const serverSeenIds = scenario?.guide_seen_features ?? NO_FEATURE_IDS;
  const { value: seenIds, commit } = useSyncedValue(serverSeenIds, (next) =>
    saveFields({ guide_seen_features: next }),
  );
  const eligible = useMemo(
    () => (createdAt ? getFeaturesReleasedAfter(createdAt) : []),
    [createdAt],
  );
  const groups = useMemo(() => splitFeaturesBySeen(eligible, seenIds), [eligible, seenIds]);

  return {
    hasScenario: Boolean(scenario),
    eligible,
    unseen: groups.unseen,
    seen: groups.seen,
    unseenCount: groups.unseen.length,
    markSeen: (featureId: string): void => commit(addSeenFeature(seenIds, featureId)),
  };
};
