import React from "react";
import { useIsAlphaMode } from "@/shared/hooks/useIsAlphaMode";
import { StudioShowcaseNarrative } from "./StudioShowcaseNarrative";
import { StudioWorkbenchPreview } from "./StudioWorkbenchPreview";
import type { StudioShowcaseBandProps } from "./StudioShowcaseBand.types";

export const StudioShowcaseBand: React.FC<StudioShowcaseBandProps> = ({
  className = "",
}) => {
  const isAlphaMode = useIsAlphaMode();
  if (isAlphaMode) return null;

  return (
    <section className={`w-full bg-surface-sunken py-8 ${className}`}>
      <div className="rounded-md border border-border-subtle bg-surface-raised p-6 md:p-10">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
          <div className="lg:col-span-6">
            <StudioShowcaseNarrative />
          </div>
          <div className="lg:col-span-6 w-full">
            <StudioWorkbenchPreview />
          </div>
        </div>
      </div>
    </section>
  );
};
