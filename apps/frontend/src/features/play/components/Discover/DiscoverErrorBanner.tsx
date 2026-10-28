import React from "react";
import { Button } from "@/shared/components/ui/Button";
import type { DiscoverErrorBannerProps } from "./DiscoverErrorBanner.types";

export const DiscoverErrorBanner: React.FC<DiscoverErrorBannerProps> = ({
  onRetry,
}) => (
  <div
    role="alert"
    className="flex items-center justify-between gap-4 rounded-md border border-danger/50 bg-danger/10 px-4 py-3 text-sm text-content"
  >
    <span>We couldn&apos;t load stories.</span>
    <Button variant="secondary" size="sm" onClick={onRetry}>
      Retry
    </Button>
  </div>
);
