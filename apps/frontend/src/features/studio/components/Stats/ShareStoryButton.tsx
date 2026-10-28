import React, { useState } from "react";
import { Button } from "@/shared/components/ui/Button";
import type { CopyState } from "../../types/statsView.types";
import type { ShareStoryButtonProps } from "./ShareStoryButton.types";

export const ShareStoryButton: React.FC<ShareStoryButtonProps> = ({ scenarioId }) => {
  const [copyState, setCopyState] = useState<CopyState>("idle");
  const copyLink = async (): Promise<void> => {
    try {
      await navigator.clipboard.writeText(
        `${window.location.origin}/scenario/${scenarioId}`,
      );
      setCopyState("copied");
    } catch {
      setCopyState("failed");
    }
  };
  const handleShare = (): void => {
    void copyLink();
  };
  return (
    <div className="flex items-center gap-3">
      <Button variant="secondary" onClick={handleShare}>
        Share your story
      </Button>
      {copyState === "copied" && (
        <span role="status" className="font-sans text-sm text-content-muted">
          Link copied
        </span>
      )}
      {copyState === "failed" && (
        <span role="alert" className="font-sans text-sm text-danger">
          Couldn&apos;t copy the link
        </span>
      )}
    </div>
  );
};
