import React, { useState } from "react";
import { Button } from "@/shared/components/ui/Button";
import { SENSORY_CUE_IDS, SensoryCueId } from "@/shared/constants/sensory-cues";
import { previewCue } from "@/shared/lib/audio/previewCue";
import { CueLibraryProps } from "./CueLibrary.types";

const labelOf = (cue: string): string => cue.replace(/_/g, " ");

export const CueLibrary: React.FC<CueLibraryProps> = ({ onPreview }) => {
  const [message, setMessage] = useState<string | null>(null);

  const handlePlay = async (cue: SensoryCueId): Promise<void> => {
    const play = onPreview ?? ((id: string) => previewCue(id as SensoryCueId));
    const result = await play(cue);
    setMessage(
      result === "blocked"
        ? "Your browser blocked the sound. Click anywhere on the page first, then try again."
        : null,
    );
  };

  return (
    <section aria-label="Cue library" className="space-y-2">
      <h2 className="text-sm font-semibold text-content">Sound cues</h2>
      <p className="text-xs text-content-faint">
        Attach a cue to an active rule in the Active Rules tab.
      </p>
      <ul className="grid grid-cols-2 gap-2">
        {SENSORY_CUE_IDS.map((cue) => (
          <li
            key={cue}
            className="rounded-md flex items-center justify-between border border-border-subtle px-3 py-1"
          >
            <span className="text-sm text-content">{labelOf(cue)}</span>
            <Button
              type="button"
              size="sm"
              variant="secondary"
              onClick={() => void handlePlay(cue)}
              aria-label={`Play ${labelOf(cue)}`}
            >
              Play
            </Button>
          </li>
        ))}
      </ul>
      {message && (
        <p role="status" className="text-xs text-warning">
          {message}
        </p>
      )}
    </section>
  );
};
