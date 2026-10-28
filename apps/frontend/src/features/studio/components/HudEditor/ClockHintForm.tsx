import React, { useState } from "react";
import { Input } from "@/shared/components/ui/Input";
import { Select } from "@/shared/components/ui/Select";
import { CLOCK_FORMATS } from "@/shared/constants/display-hints";
import type { ClockFormat, ClockHint } from "@/shared/types/display-hints.types";
import { ClockHintFormProps } from "./ClockHintForm.types";
import { DEFAULT_CLOCK, clockProblems } from "./hudHints";
import { FieldPickerSection } from "./FieldPickerSection";

const DEFAULT_GLITCH_BELOW = 25;
const DEFAULT_GLITCH_CHANCE = 0.02;

export const ClockHintForm: React.FC<ClockHintFormProps> = ({
  current,
  numberFields,
  meterFields,
  isSaving,
  onSave,
  onRemove,
}) => {
  const [path, setPath] = useState(current?.path ?? "");
  const [hint, setHint] = useState<ClockHint>(current?.hint ?? DEFAULT_CLOCK);
  const glitchSource = hint.glitch?.source ?? "";

  const handleGlitchSource = (source: string): void =>
    setHint({
      ...hint,
      glitch: source
        ? {
            source,
            below: hint.glitch?.below ?? DEFAULT_GLITCH_BELOW,
            chance: hint.glitch?.chance ?? DEFAULT_GLITCH_CHANCE,
          }
        : undefined,
    });

  const sourceOptions = [
    { value: "", label: "No glitch" },
    ...meterFields.map((meter) => ({
      value: meter.path,
      label: `${meter.label} (${meter.path})`,
    })),
  ];

  return (
    <FieldPickerSection
      title="Clock"
      fieldLabel="Clock value"
      fields={numberFields}
      path={path}
      isPathLocked={Boolean(current)}
      problems={clockProblems(hint)}
      isSaving={isSaving}
      onPathChange={setPath}
      onSave={() => onSave(path, hint)}
      onRemove={current ? () => onRemove(current.path) : undefined}
    >
      <p className="text-xs text-content-faint">
        The value counts minutes since the start time.
      </p>
      <div className="grid grid-cols-3 gap-2">
        <Input
          aria-label="Clock label"
          value={hint.label}
          onChange={(event) => setHint({ ...hint, label: event.target.value })}
        />
        <Input
          aria-label="Clock start time"
          value={hint.start}
          placeholder="23:00"
          onChange={(event) => setHint({ ...hint, start: event.target.value })}
        />
        <Select
          aria-label="Clock format"
          options={CLOCK_FORMATS.map((format) => ({ value: format, label: format }))}
          value={hint.format}
          onChange={(event) =>
            setHint({ ...hint, format: event.target.value as ClockFormat })
          }
        />
      </div>
      <Select
        aria-label="Glitch the clock when this meter is low"
        options={sourceOptions}
        value={glitchSource}
        onChange={(event) => handleGlitchSource(event.target.value)}
      />
      {hint.glitch && (
        <div className="grid grid-cols-2 gap-2">
          <Input
            aria-label="Glitch below"
            type="number"
            value={hint.glitch.below}
            onChange={(event) =>
              setHint({
                ...hint,
                glitch: { ...hint.glitch!, below: Number(event.target.value) },
              })
            }
          />
          <Input
            aria-label="Glitch chance"
            type="number"
            step={0.01}
            min={0}
            max={1}
            value={hint.glitch.chance}
            onChange={(event) =>
              setHint({
                ...hint,
                glitch: { ...hint.glitch!, chance: Number(event.target.value) },
              })
            }
          />
        </div>
      )}
    </FieldPickerSection>
  );
};
