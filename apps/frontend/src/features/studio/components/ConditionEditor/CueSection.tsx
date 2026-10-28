import React, { useState } from "react";
import { Button } from "@/shared/components/ui/Button";
import { Select } from "@/shared/components/ui/Select";
import { SENSORY_CUE_IDS, SensoryCueId } from "@/shared/constants/sensory-cues";
import { previewCue } from "@/shared/lib/audio/previewCue";
import { MAX_SILENCE_DURATION_MS } from "../../constants/condition";
import { CueSectionProps } from "./CueSection.types";

const SILENCE_STEP_MS = 100;
const CUE_OPTIONS = [
  { value: "", label: "No sound cue" },
  ...SENSORY_CUE_IDS.map((cue) => ({ value: cue, label: cue.replace(/_/g, " ") })),
];

export const CueSection: React.FC<CueSectionProps> = ({
  value,
  onChange,
  onPreview,
}) => {
  const [isBlocked, setIsBlocked] = useState(false);

  const handlePlay = async (): Promise<void> => {
    const play = onPreview ?? ((id: string) => previewCue(id as SensoryCueId));
    setIsBlocked((await play(value.cue)) === "blocked");
  };

  return (
    <fieldset className="rounded-md space-y-2 border border-border-subtle p-3">
      <legend className="px-1 text-sm text-content-muted">Sound cue</legend>
      <div className="flex items-center gap-2">
        <Select
          aria-label="Sound cue"
          options={CUE_OPTIONS}
          value={value.cue}
          onChange={(event) => onChange({ ...value, cue: event.target.value })}
        />
        <Button
          type="button"
          size="sm"
          variant="secondary"
          disabled={!value.cue}
          onClick={() => void handlePlay()}
        >
          Play cue
        </Button>
      </div>
      {isBlocked && (
        <p role="status" className="text-xs text-warning">
          Your browser blocked the sound. Click the page first, then try again.
        </p>
      )}
      {value.cue && (
        <>
          <label className="flex items-center gap-2 text-sm text-content-muted">
            <input
              type="checkbox"
              checked={value.cutAmbient}
              onChange={(event) =>
                onChange({ ...value, cutAmbient: event.target.checked })
              }
            />
            Cut the ambience first
          </label>
          <label className="block text-sm text-content-muted">
            {`Silence before the cue: ${value.silenceMs} ms`}
            <input
              type="range"
              aria-label="Silence before the cue"
              min={0}
              max={MAX_SILENCE_DURATION_MS}
              step={SILENCE_STEP_MS}
              value={value.silenceMs}
              onChange={(event) =>
                onChange({ ...value, silenceMs: Number(event.target.value) })
              }
              className="block w-full"
            />
          </label>
        </>
      )}
    </fieldset>
  );
};
