import React from "react";
import { IconBook2 } from "@tabler/icons-react";

export const SetupStageEmptyState: React.FC = () => (
  <div className="text-center py-8 px-4 bg-surface-inset border border-border-subtle rounded-md space-y-3">
    <div className="w-10 h-10 mx-auto rounded-full bg-surface-raised border border-border-subtle flex items-center justify-center text-content-muted">
      <IconBook2 size={20} stroke={1.5} aria-hidden="true" />
    </div>
    <p className="font-sans text-sm text-content-muted italic">
      No character customization is required for this scenario.
    </p>
    <p className="font-mono text-xs text-content-faint">
      The chronicle begins immediately upon departure.
    </p>
  </div>
);
