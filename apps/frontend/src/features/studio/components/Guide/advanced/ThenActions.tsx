import React, { useRef, useState } from "react";
import { Button } from "@/shared/components/ui/Button";
import { MAX_RULE_CHANGES } from "../../../constants/rules";
import { buildEmptyChangeRow } from "../../../lib/changeRows";
import { CueSection } from "../../ConditionEditor/CueSection";
import type { ThenActionsProps } from "./Advanced.types";
import { ChangeRowFields } from "./ChangeRowFields";
import { FieldBlock } from "./FieldBlock";

export const ThenActions: React.FC<ThenActionsProps> = ({ draft, options, onChange, onSoundChange }) => {
  const [isSoundOpen, setIsSoundOpen] = useState(false);
  const addedCount = useRef(0);
  const isSoundShown = isSoundOpen || draft.sound.cue !== "";
  const patchChange = (index: number, next: (typeof draft.changes)[number]): void =>
    onChange({ ...draft, changes: draft.changes.map((row, at) => (at === index ? next : row)) });

  const handleAddChange = (): void => {
    addedCount.current += 1;
    onChange({ ...draft, changes: [...draft.changes, buildEmptyChangeRow(`added-${addedCount.current}`)] });
  };

  return (
    <FieldBlock label="Then">
      <div className="space-y-3">
        <label className="block space-y-1 text-meta text-content-muted">
          Tell the narrator
          <textarea
            value={draft.instruction}
            rows={2}
            onChange={(event) => onChange({ ...draft, instruction: event.target.value })}
            className="w-full resize-y rounded-sm border border-border-strong bg-surface-inset px-3 py-2 text-body text-content placeholder:text-content-faint focus:border-primary focus:outline-hidden"
          />
        </label>
        {draft.changes.map((row, index) => (
          <ChangeRowFields
            key={row.id}
            row={row}
            rowLabel={`Change ${index + 1}`}
            options={options}
            onChange={(next) => patchChange(index, next)}
            onRemove={() => onChange({ ...draft, changes: draft.changes.filter((_, at) => at !== index) })}
          />
        ))}
        <div className="flex flex-wrap gap-2">
          {draft.changes.length < MAX_RULE_CHANGES && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={handleAddChange}
            >
              + Change a value
            </Button>
          )}
          {!isSoundShown && (
            <Button type="button" variant="ghost" size="sm" onClick={() => setIsSoundOpen(true)}>
              + Sound
            </Button>
          )}
        </div>
        {isSoundShown && <CueSection value={draft.sound} onChange={onSoundChange} />}
      </div>
    </FieldBlock>
  );
};
