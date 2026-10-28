import { useEffect } from "react";
import { useNewFeaturesStore } from "../stores/newFeatures.store";
import { useNewFeatures } from "./useNewFeatures";

export const useSyncFeatureHints = (): void => {
  const { unseen } = useNewFeatures();
  const setUnseenFeatureIds = useNewFeaturesStore((state) => state.setUnseenFeatureIds);
  const unseenKey = unseen.map((feature) => feature.id).join(",");

  useEffect(() => {
    setUnseenFeatureIds(unseenKey ? unseenKey.split(",") : []);
    return () => setUnseenFeatureIds([]);
  }, [setUnseenFeatureIds, unseenKey]);
};
