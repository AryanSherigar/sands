import React from "react";

export const JobInProgress: React.FC = () => (
  <p className="text-xs text-content-muted flex items-center gap-2">
    <span className="h-3 w-3 animate-spin rounded-full border-2 border-content-muted border-t-transparent" />
    Generating…
  </p>
);
