import React, { useState } from "react";
import { AudioPreviewPlayer } from "@/shared/components/AudioPreviewPlayer";
import { extractErrorMessage } from "@/shared/lib/extractErrorMessage";
import { useScenarioMusic } from "../../hooks/useScenarioMusic";
import { MoodSlotCardProps } from "./MoodSlotCard.types";
import { MoodSlotUploadRow } from "./MoodSlotUploadRow";

const getSourceLabel = (source?: string): string => {
  if (source === "upload") return "Uploaded";
  return "Default track";
};

export const MoodSlotCard: React.FC<MoodSlotCardProps> = ({
  scenarioId,
  mood,
  label,
  slot,
}) => {
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const {
    uploadTrack,
    isUploading,
    setDefaultTrack,
  } = useScenarioMusic(scenarioId);
  const isBusy = isUploading;
  const effectiveTrackUrl = slot?.track_url ?? null;

  const handleFileSelected = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setErrorMessage(null);
    uploadTrack(
      { mood, file },
      {
        onError: (err) =>
          setErrorMessage(
            extractErrorMessage(err, "Upload failed — please try again."),
          ),
      },
    );
  };

  return (
    <div className="rounded-lg border border-border-subtle bg-surface-inset p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-content">{label}</h3>
        <span className="text-xs uppercase tracking-wide text-content-faint">
          {getSourceLabel(slot?.source)}
        </span>
      </div>

      {effectiveTrackUrl && <AudioPreviewPlayer src={effectiveTrackUrl} />}

      <MoodSlotUploadRow
        label={label}
        isBusy={isBusy}
        isUploading={isUploading}
        isCustomTrack={slot?.source !== "default"}
        onFileSelect={handleFileSelected}
        onUseDefault={() => setDefaultTrack(mood)}
      />

      {errorMessage && <p className="text-xs text-danger">{errorMessage}</p>}
    </div>
  );
};
