import React, { useState } from "react";
import { Button } from "@/shared/components/ui/Button";
import { Input } from "@/shared/components/ui/Input";
import type { MeterEffects } from "@/shared/types/display-hints.types";
import {
  MAX_INTRUSIVE_THOUGHTS,
  MAX_THOUGHT_LENGTH,
  THRESHOLDS,
  effectsProblems,
} from "./readerEffects";
import { ReaderEffectsFormProps } from "./ReaderEffectsForm.types";

export const ReaderEffectsForm: React.FC<ReaderEffectsFormProps> = ({
  path,
  hint,
  isSaving,
  onSave,
}) => {
  const [effects, setEffects] = useState<MeterEffects>(hint.effects ?? {});
  const thoughts = effects.intrusive_thoughts ?? [];
  const problems = effectsProblems(effects);

  const setThoughts = (next: string[]): void =>
    setEffects({ ...effects, intrusive_thoughts: next });

  const handleSave = (): void => {
    const hasAny = Object.values(effects).some((value) =>
      Array.isArray(value) ? value.length > 0 : value !== undefined,
    );
    onSave(path, { ...hint, effects: hasAny ? effects : undefined });
  };

  return (
    <section aria-label={`Reader effects for ${hint.label}`} className="space-y-3">
      <h2 className="text-sm font-semibold text-content">{`Reader effects (${hint.label})`}</h2>
      <p className="text-xs text-content-faint">
        As {hint.label} falls below these values the reader changes. Leave a
        field blank to switch that effect off.
      </p>
      <div className="grid grid-cols-3 gap-2">
        {THRESHOLDS.map(([key, label]) => (
          <Input
            key={key}
            aria-label={label}
            type="number"
            placeholder={label}
            value={effects[key] ?? ""}
            onChange={(event) =>
              setEffects({
                ...effects,
                [key]: event.target.value === "" ? undefined : Number(event.target.value),
              })
            }
          />
        ))}
      </div>
      <ul className="space-y-2">
        {thoughts.map((text, index) => (
          <li key={index} className="flex items-center gap-2">
            <Input
              aria-label={`Intrusive thought ${index + 1}`}
              value={text}
              maxLength={MAX_THOUGHT_LENGTH + 20}
              onChange={(event) =>
                setThoughts(thoughts.map((t, i) => (i === index ? event.target.value : t)))
              }
            />
            <Button
              type="button"
              size="sm"
              variant="danger"
              aria-label={`Remove thought ${index + 1}`}
              onClick={() => setThoughts(thoughts.filter((_, i) => i !== index))}
            >
              Remove
            </Button>
          </li>
        ))}
      </ul>
      <Button
        type="button"
        size="sm"
        variant="secondary"
        disabled={thoughts.length >= MAX_INTRUSIVE_THOUGHTS}
        onClick={() => setThoughts([...thoughts, ""])}
      >
        Add intrusive thought
      </Button>
      {problems.length > 0 && (
        <ul role="alert" className="list-disc pl-5 text-xs text-warning">
          {problems.map((problem) => (
            <li key={problem}>{problem}</li>
          ))}
        </ul>
      )}
      <Button
        type="button"
        size="sm"
        disabled={problems.length > 0 || isSaving}
        onClick={handleSave}
      >
        Save reader effects
      </Button>
    </section>
  );
};
