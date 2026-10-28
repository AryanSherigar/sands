import React, { useState } from "react";
import { Button } from "@/shared/components/ui/Button";
import {
  ADVANCED_FEATURE_HINT,
  ADVANCED_FEATURE_LABEL,
} from "../../constants/newFeatures";
import { useGuide } from "../../hooks/useGuide";
import { useNewFeatures } from "../../hooks/useNewFeatures";
import { useShowFeature } from "../../hooks/useShowFeature";
import { formatReleaseDate } from "../../lib/newFeatures";
import type { NewFeatureTabProps } from "./NewFeatures.types";

export const NewFeatureTab: React.FC<NewFeatureTabProps> = ({
  feature,
  isAdvancedOn,
}) => {
  const { scenario } = useGuide();
  const { seen, markSeen } = useNewFeatures();
  const showFeature = useShowFeature();
  const [shouldShowAdvancedHint, setShouldShowAdvancedHint] = useState(false);
  const isSeen = seen.some((entry) => entry.id === feature.id);
  const isBlockedByAdvanced = feature.isAdvanced && !(isAdvancedOn ?? scenario?.mode === "master");

  const handleShowMe = (): void => {
    if (isBlockedByAdvanced) {
      setShouldShowAdvancedHint(true);
      return;
    }
    showFeature(feature);
  };

  return (
    <article className="mx-auto w-full max-w-[640px] space-y-6 px-4 py-8 md:py-12">
      <header className="space-y-2">
        <div className="flex flex-wrap items-center gap-2 text-micro text-content-muted">
          <span className="rounded-sm border border-primary/40 bg-primary/10 px-1.5 py-0.5 font-medium text-primary">
            New · {formatReleaseDate(feature.releasedOn)}
          </span>
          {feature.isAdvanced && (
            <span className="rounded-sm border border-border-strong px-1.5 py-0.5">
              {ADVANCED_FEATURE_LABEL}
            </span>
          )}
        </div>
        <h1 className="text-title font-semibold text-content">{feature.name}</h1>
        <p className="text-body text-content-muted">{feature.description}</p>
      </header>
      <section aria-label="Example" className="rounded-md border border-border-subtle bg-surface-inset p-4">
        <p className="text-meta text-content">{feature.example}</p>
      </section>
      <section aria-label="Where to find it" className="space-y-1">
        <h2 className="text-meta font-medium text-content-muted">Where to find it</h2>
        <p className="text-body text-content">{feature.location}</p>
      </section>
      {shouldShowAdvancedHint && (
        <p role="status" className="text-meta text-warning">
          {ADVANCED_FEATURE_HINT}
        </p>
      )}
      <div className="flex items-center gap-2">
        <Button type="button" variant="secondary" onClick={handleShowMe}>
          Show me
        </Button>
        {isSeen ? (
          <span className="text-meta text-content-muted">Seen</span>
        ) : (
          <Button type="button" onClick={() => markSeen(feature.id)}>
            Got it
          </Button>
        )}
      </div>
    </article>
  );
};
