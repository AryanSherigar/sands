import React from "react";
import { ButtonLink } from "@/shared/components/ui/ButtonLink";
import type { DraftBannerProps } from "./DraftBanner.types";

export const DraftBanner: React.FC<DraftBannerProps> = ({ scenarioId }) => (
  <div
    role="status"
    className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-border-strong bg-surface-raised px-4 py-3 font-sans text-sm text-content"
  >
    <span>Draft — only you can see this page</span>
    <ButtonLink to={`/studio/${scenarioId}`} variant="secondary" size="sm">
      Edit in Studio
    </ButtonLink>
  </div>
);
