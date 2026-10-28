import React from "react";
import { Button } from "@/shared/components/ui/Button";
import { MusicGenerationJob } from "../../types/music.types";
import { JobInProgress } from "./JobInProgress";
import { JobSucceeded } from "./JobSucceeded";

interface MoodSlotJobStatusProps {
  job: MusicGenerationJob;
  isConfirming: boolean;
  onConfirm: () => void;
  onDiscard: () => void;
}

export const MoodSlotJobStatus: React.FC<MoodSlotJobStatusProps> = ({
  job,
  isConfirming,
  onConfirm,
  onDiscard,
}) => {
  const isRunning = job.status === "pending" || job.status === "running";

  return (
    <div className="space-y-2 pt-2 border-t border-border-subtle">
      {isRunning && <JobInProgress />}
      {job.status === "succeeded" && (
        <JobSucceeded
          previewUrl={job.preview_url}
          isConfirming={isConfirming}
          onConfirm={onConfirm}
          onDiscard={onDiscard}
        />
      )}
      {job.status === "failed" && (
        <>
          <p className="text-xs text-danger">
            {job.error_message || "Generation failed."}
          </p>
          <Button type="button" variant="ghost" size="sm" onClick={onDiscard}>
            Dismiss
          </Button>
        </>
      )}
    </div>
  );
};
