import React from "react";
import { cn } from "@/shared/lib/cn";
import { useNewFeaturesStore } from "../../stores/newFeatures.store";
import type { FeatureAnchorProps } from "./NewFeatures.types";

export const FeatureAnchor: React.FC<FeatureAnchorProps> = ({
  featureId,
  className,
  children,
}) => {
  const isNew = useNewFeaturesStore((state) => state.unseenFeatureIds.includes(featureId));
  const isHighlighted = useNewFeaturesStore((state) => state.highlightedFeatureId === featureId);

  return (
    <div
      data-feature-id={featureId}
      data-highlighted={isHighlighted ? "true" : undefined}
      className={cn(
        "rounded-md transition-shadow",
        isHighlighted && "ring-2 ring-primary ring-offset-2 ring-offset-surface-raised",
        className,
      )}
    >
      {isNew && (
        <span className="mb-1 inline-block rounded-sm border border-primary/40 bg-primary/10 px-1.5 py-0.5 text-micro font-medium text-primary">
          New
        </span>
      )}
      {children}
    </div>
  );
};
