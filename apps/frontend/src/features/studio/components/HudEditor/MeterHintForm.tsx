import React, { useState } from "react";
import { Button } from "@/shared/components/ui/Button";
import { Input } from "@/shared/components/ui/Input";
import type { MeterHint, MeterTier } from "@/shared/types/display-hints.types";
import { FieldPickerSection } from "./FieldPickerSection";
import { MeterHintFormProps } from "./MeterHintForm.types";
import { DEFAULT_METER, meterProblems } from "./hudHints";

export const MeterHintForm: React.FC<MeterHintFormProps> = ({
  current,
  numberFields,
  isSaving,
  onSave,
  onRemove,
}) => {
  const [path, setPath] = useState(current?.path ?? "");
  const [hint, setHint] = useState<MeterHint>(current?.hint ?? DEFAULT_METER);
  const tiers = hint.tiers ?? [];

  const setTiers = (next: MeterTier[]): void =>
    setHint({ ...hint, tiers: next.length ? next : undefined });

  const handleTierChange = (index: number, patch: Partial<MeterTier>): void =>
    setTiers(tiers.map((tier, i) => (i === index ? { ...tier, ...patch } : tier)));

  return (
    <FieldPickerSection
      title="Meter"
      fieldLabel="Meter value"
      fields={numberFields}
      path={path}
      isPathLocked={Boolean(current)}
      problems={meterProblems(hint)}
      isSaving={isSaving}
      onPathChange={setPath}
      onSave={() => onSave(path, hint)}
      onRemove={current ? () => onRemove(current.path) : undefined}
    >
      <div className="grid grid-cols-3 gap-2">
        <Input
          aria-label="Meter label"
          value={hint.label}
          onChange={(event) => setHint({ ...hint, label: event.target.value })}
        />
        <Input
          aria-label="Lowest shown value"
          type="number"
          value={hint.clamp_min}
          onChange={(event) =>
            setHint({ ...hint, clamp_min: Number(event.target.value) })
          }
        />
        <Input
          aria-label="Highest shown value"
          type="number"
          value={hint.clamp_max}
          onChange={(event) =>
            setHint({ ...hint, clamp_max: Number(event.target.value) })
          }
        />
      </div>
      <ul className="space-y-2">
        {tiers.map((tier, index) => (
          <li key={index} className="flex items-center gap-2">
            <Input
              aria-label={`Tier ${index + 1} name`}
              value={tier.name}
              onChange={(event) => handleTierChange(index, { name: event.target.value })}
            />
            <Input
              aria-label={`Tier ${index + 1} minimum`}
              type="number"
              placeholder="no minimum"
              value={tier.min ?? ""}
              onChange={(event) =>
                handleTierChange(index, {
                  min: event.target.value === "" ? undefined : Number(event.target.value),
                })
              }
            />
            <Button
              type="button"
              size="sm"
              variant="danger"
              onClick={() => setTiers(tiers.filter((_, i) => i !== index))}
              aria-label={`Remove tier ${index + 1}`}
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
        onClick={() => setTiers([...tiers, { name: "" }])}
      >
        Add tier
      </Button>
    </FieldPickerSection>
  );
};
