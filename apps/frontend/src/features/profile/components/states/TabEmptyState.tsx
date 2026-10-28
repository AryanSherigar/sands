import React from "react";
import { ButtonLink } from "@/shared/components/ui/ButtonLink";
import type { TabEmptyStateProps } from "./TabEmptyState.types";

export const TabEmptyState: React.FC<TabEmptyStateProps> = ({
  message,
  action,
}) => (
  <div className="flex flex-col items-center gap-4 rounded-md border border-dashed border-border-strong px-6 py-12 text-center">
    <p className="text-sm text-content-muted">{message}</p>
    {action && (
      <ButtonLink to={action.to} variant="secondary" size="sm">
        {action.label}
      </ButtonLink>
    )}
  </div>
);
