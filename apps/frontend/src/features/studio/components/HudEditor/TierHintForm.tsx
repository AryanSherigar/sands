import React, { useState } from "react";
import { Input } from "@/shared/components/ui/Input";
import type { TierHint } from "@/shared/types/display-hints.types";
import { FieldPickerSection } from "./FieldPickerSection";
import { TierHintFormProps } from "./TierHintForm.types";
import { DEFAULT_TIER } from "./hudHints";

export const TierHintForm: React.FC<TierHintFormProps> = ({
  current,
  enumFields,
  isSaving,
  onSave,
  onRemove,
}) => {
  const [path, setPath] = useState(current?.path ?? "");
  const [hint, setHint] = useState<TierHint>(current?.hint ?? DEFAULT_TIER);
  const problems = hint.label.trim() ? [] : ["The tier needs a label."];

  return (
    <FieldPickerSection
      title="Tension tier"
      fieldLabel="Tier value"
      fields={enumFields}
      path={path}
      isPathLocked={Boolean(current)}
      problems={problems}
      isSaving={isSaving}
      onPathChange={setPath}
      onSave={() => onSave(path, hint)}
      onRemove={current ? () => onRemove(current.path) : undefined}
    >
      <Input
        aria-label="Tier label"
        value={hint.label}
        onChange={(event) => setHint({ ...hint, label: event.target.value })}
      />
      <p className="text-xs text-content-faint">
        The options of the chosen value become the pips, in order. Music for each
        option is set in the Atmosphere tab.
      </p>
    </FieldPickerSection>
  );
};
