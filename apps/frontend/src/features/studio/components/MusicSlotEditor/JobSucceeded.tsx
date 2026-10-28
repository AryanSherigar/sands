import React from "react";
import { Button } from "@/shared/components/ui/Button";
import { AudioPreviewPlayer } from "@/shared/components/AudioPreviewPlayer";

interface JobSucceededProps {
  previewUrl?: string | null;
  isConfirming: boolean;
  onConfirm: () => void;
  onDiscard: () => void;
}

export const JobSucceeded: React.FC<JobSucceededProps> = ({
  previewUrl,
  isConfirming,
  onConfirm,
  onDiscard,
}) => {
  if (!previewUrl) {
    return (
      <>
        <p className="text-xs text-danger">
          Track generated, but preview is unavailable.
        </p>
        <Button type="button" variant="ghost" size="sm" onClick={onDiscard}>
          Discard
        </Button>
      </>
    );
  }
  return (
    <>
      <AudioPreviewPlayer src={previewUrl} />
      <div className="flex gap-2">
        <Button
          type="button"
          variant="primary"
          size="sm"
          disabled={isConfirming}
          onClick={onConfirm}
        >
          {isConfirming ? "Saving…" : "Confirm"}
        </Button>
        <Button type="button" variant="ghost" size="sm" onClick={onDiscard}>
          Discard
        </Button>
      </div>
    </>
  );
};
