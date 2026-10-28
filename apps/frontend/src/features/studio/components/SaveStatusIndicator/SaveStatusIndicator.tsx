import React from "react";
import { IconAlertTriangle } from "@tabler/icons-react";
import { SaveStatusIndicatorProps } from "./SaveStatusIndicator.types";

export const SaveStatusIndicator: React.FC<SaveStatusIndicatorProps> = ({
  isSaving,
  lastSaved,
  hasError = false,
  onRetry,
}) => {
  if (isSaving) {
    return (
      <span className="flex items-center gap-2 text-content-muted">
        <span className="h-3 w-3 animate-spin rounded-full border-b-2 border-content-muted" />
        Saving…
      </span>
    );
  }
  if (hasError) {
    return (
      <span className="flex items-center gap-2 text-danger">
        <IconAlertTriangle size={14} aria-hidden="true" />
        Couldn't save —
        <button
          type="button"
          onClick={onRetry}
          className="font-medium underline underline-offset-2 hover:text-content"
        >
          Retry
        </button>
      </span>
    );
  }
  if (lastSaved) {
    return <span className="text-success">Saved</span>;
  }
  return <span className="text-content-faint">All changes saved</span>;
};
