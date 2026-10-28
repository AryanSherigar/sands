import React, { useState } from "react";
import { Button } from "@/shared/components/ui/Button";
import { Select } from "@/shared/components/ui/Select";
import { SCENARIO_MOODS } from "@/shared/constants/audio";
import { TensionAudioFormProps } from "./TensionAudioForm.types";

const NO_MOOD = { value: "", label: "Keep the narrator's music" };
const MOOD_OPTIONS = [
  NO_MOOD,
  ...SCENARIO_MOODS.map((mood) => ({ value: mood, label: mood })),
];

export const TensionAudioForm: React.FC<TensionAudioFormProps> = ({
  path,
  hint,
  options,
  isSaving,
  onSave,
}) => {
  const [moods, setMoods] = useState<Record<string, string>>(hint.mood_map ?? {});

  const handleSave = (): void => {
    const filled = Object.fromEntries(
      Object.entries(moods).filter(([, mood]) => mood !== ""),
    );
    onSave(path, {
      ...hint,
      mood_map: Object.keys(filled).length ? filled : undefined,
    });
  };

  return (
    <section aria-label={`Music for ${hint.label}`} className="space-y-3">
      <h2 className="text-sm font-semibold text-content">{`Music for ${hint.label}`}</h2>
      <p className="text-xs text-content-faint">
        When a mood is set for a level, it replaces the narrator's own choice of music.
      </p>
      {options.map((option) => (
        <label key={option} className="flex items-center justify-between gap-2 text-sm text-content-muted">
          {option}
          <Select
            aria-label={`Music for ${option}`}
            options={MOOD_OPTIONS}
            value={moods[option] ?? ""}
            onChange={(event) => setMoods({ ...moods, [option]: event.target.value })}
          />
        </label>
      ))}
      <Button type="button" size="sm" disabled={isSaving} onClick={handleSave}>
        Save music
      </Button>
    </section>
  );
};
