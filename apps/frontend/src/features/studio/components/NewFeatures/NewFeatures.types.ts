import type { ReactNode } from "react";
import type { NewFeature } from "../../constants/newFeatures";

export interface FeatureAnchorProps {
  featureId: string;
  className?: string;
  children: ReactNode;
}

export interface NewFeatureTabProps {
  feature: NewFeature;
  isAdvancedOn?: boolean;
}
