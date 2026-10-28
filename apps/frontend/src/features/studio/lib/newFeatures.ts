import { NEW_FEATURES, type NewFeature } from "../constants/newFeatures";

export interface FeatureGroups {
  unseen: NewFeature[];
  seen: NewFeature[];
}

export const getFeatureById = (
  featureId: string,
  features: readonly NewFeature[] = NEW_FEATURES,
): NewFeature | null => features.find((feature) => feature.id === featureId) ?? null;

export const getFeaturesReleasedAfter = (
  createdAt: string,
  features: readonly NewFeature[] = NEW_FEATURES,
): NewFeature[] => {
  const createdTime = new Date(createdAt).getTime();
  return features.filter((feature) => new Date(feature.releasedOn).getTime() > createdTime);
};

export const splitFeaturesBySeen = (
  eligible: NewFeature[],
  seenIds: readonly string[],
): FeatureGroups => ({
  unseen: eligible.filter((feature) => !seenIds.includes(feature.id)),
  seen: eligible.filter((feature) => seenIds.includes(feature.id)),
});

export const addSeenFeature = (seenIds: readonly string[], featureId: string): string[] =>
  seenIds.includes(featureId) ? [...seenIds] : [...seenIds, featureId];

export const formatReleaseDate = (releasedOn: string): string =>
  new Date(releasedOn).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  });
