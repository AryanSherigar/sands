import React from "react";
import { Input } from "@/shared/components/ui/Input";
import { Select } from "@/shared/components/ui/Select";
import type {
  ComposureAudioProfile,
  ComposureKey,
} from "@/shared/types/minigame.types";
import { ComposureConfigSectionProps } from "./ComposureConfigSection.types";

const KEYS: ComposureKey[] = ["W", "A", "S", "D"];
const TEXT_FIELDS = ["instructions", "start_text", "win_text", "lose_text"] as const;
const PROFILE_OPTIONS = [
  { value: "chase", label: "Chase (closing footsteps)" },
  { value: "hum", label: "Hum (calm pulse)" },
];

interface NumberFieldSpec {
  key: "target_bpm" | "beats_to_win" | "tolerance_ms" | "max_strikes";
  label: string;
  min: number;
  max: number;
}
const NUMBER_FIELDS: NumberFieldSpec[] = [
  { key: "target_bpm", label: "Tempo (beats per minute)", min: 30, max: 120 },
  { key: "beats_to_win", label: "Hits in a row to win", min: 3, max: 12 },
  { key: "tolerance_ms", label: "Timing tolerance (ms)", min: 80, max: 400 },
  { key: "max_strikes", label: "Strikes allowed", min: 1, max: 5 },
];

export const ComposureConfigSection: React.FC<ComposureConfigSectionProps> = ({
  config,
  onChange,
}) => {
  const handleKeyToggle = (key: ComposureKey): void => {
    const has = config.keys.includes(key);
    if (has && config.keys.length === 1) return;
    const keys = has
      ? config.keys.filter((item) => item !== key)
      : KEYS.filter((item) => item === key || config.keys.includes(item));
    onChange({ ...config, keys });
  };

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-2">
        {NUMBER_FIELDS.map((field) => (
          <label key={field.key} className="block text-xs text-content-muted">
            {field.label}
            <Input
              aria-label={field.label}
              type="number"
              min={field.min}
              max={field.max}
              value={config[field.key]}
              onChange={(event) =>
                onChange({ ...config, [field.key]: Number(event.target.value) })
              }
            />
          </label>
        ))}
      </div>
      <fieldset className="flex items-center gap-3 text-sm text-content-muted">
        <legend className="mb-1 text-xs">Keys (matched by position, not letter)</legend>
        {KEYS.map((key) => (
          <label key={key} className="flex items-center gap-1">
            <input
              type="checkbox"
              aria-label={`Key ${key}`}
              checked={config.keys.includes(key)}
              onChange={() => handleKeyToggle(key)}
            />
            {key}
          </label>
        ))}
      </fieldset>
      <Select
        aria-label="Sound profile"
        options={PROFILE_OPTIONS}
        value={config.audio_profile}
        onChange={(event) =>
          onChange({
            ...config,
            audio_profile: event.target.value as ComposureAudioProfile,
          })
        }
      />
      <div className="grid grid-cols-2 gap-2">
        {TEXT_FIELDS.map((field) => (
          <Input
            key={field}
            aria-label={`Composure ${field.replace("_", " ")}`}
            value={config.texts[field]}
            onChange={(event) =>
              onChange({
                ...config,
                texts: { ...config.texts, [field]: event.target.value },
              })
            }
          />
        ))}
      </div>
    </div>
  );
};
