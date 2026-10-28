import React, { useId } from "react";
import { Button } from "@/shared/components/ui/Button";
import type { FinishActionsProps } from "./Guide.types";

const getPublishLabel = ({ isBusy, isLive, failureMessage }: FinishActionsProps): string => {
  if (isBusy) return "Publishing…";
  if (failureMessage) return "Try again";
  return isLive ? "Publish changes" : "Publish";
};

export const FinishActions: React.FC<FinishActionsProps> = (props) => {
  const { isPublishDisabled, missingMessage, failureMessage, onPlaytest, onPublish } = props;
  const messageId = useId();

  return (
    <div className="space-y-3">
      {failureMessage && (
        <p role="alert" className="rounded-md border border-danger/40 bg-danger/10 px-3 py-2 text-meta text-danger">
          {failureMessage}
        </p>
      )}
      <div className="flex flex-wrap items-center gap-2">
        <Button type="button" variant="secondary" onClick={onPlaytest}>
          Playtest first
        </Button>
        <Button
          type="button"
          disabled={isPublishDisabled}
          aria-describedby={missingMessage ? messageId : undefined}
          onClick={onPublish}
        >
          {getPublishLabel(props)}
        </Button>
      </div>
      {missingMessage && (
        <p id={messageId} className="text-meta text-content-muted">
          {missingMessage}
        </p>
      )}
    </div>
  );
};
