import React, { useState } from "react";
import { Button } from "@/shared/components/ui/Button";
import { Input } from "@/shared/components/ui/Input";
import { Select } from "@/shared/components/ui/Select";
import { logEvent } from "@/shared/lib/logger";
import { NEW_VALUE_FAILED_MESSAGE, NEW_VALUE_KIND_OPTIONS } from "../../constants/sentenceBuilder";
import { useNewValueForm } from "../../hooks/useNewValueForm";
import { useTrackedValues } from "../../hooks/useTrackedValues";
import type { ValueKind } from "../../types/sentence.types";
import { NewValueFields } from "./NewValueFields";
import type { NewValueInlineProps } from "./SentenceBuilder.types";

export const NewValueInline: React.FC<NewValueInlineProps> = ({ onCreated, onCancel }) => {
  const { addValue } = useTrackedValues();
  const form = useNewValueForm();
  const [isSaving, setIsSaving] = useState(false);
  const [hasFailed, setHasFailed] = useState(false);

  const handleAdd = async (): Promise<void> => {
    setIsSaving(true);
    setHasFailed(false);
    try {
      onCreated(await addValue(form.buildInput()));
    } catch (error) {
      logEvent("warning", "tracked_value_create_failed", { error: String(error) });
      setHasFailed(true);
      setIsSaving(false);
    }
  };

  return (
    <div
      role="group"
      aria-label="New tracked value"
      className="space-y-3 rounded-md border border-border-subtle bg-surface-inset p-3"
    >
      <div className="flex flex-wrap items-end gap-3">
        <label className="space-y-1 text-meta text-content-muted">
          Name
          <Input value={form.fields.name} onChange={(event) => form.setters.setName(event.target.value)} />
        </label>
        <label className="space-y-1 text-meta text-content-muted">
          Type
          <Select
            value={form.fields.kind}
            options={NEW_VALUE_KIND_OPTIONS}
            onChange={(event) => form.setters.setKind(event.target.value as ValueKind)}
          />
        </label>
        <NewValueFields form={form} />
      </div>
      {hasFailed && (
        <p role="alert" className="text-meta text-danger">
          {NEW_VALUE_FAILED_MESSAGE}
        </p>
      )}
      <div className="flex gap-2">
        <Button type="button" size="sm" disabled={!form.isComplete || isSaving} onClick={() => void handleAdd()}>
          Add value
        </Button>
        <Button type="button" size="sm" variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
      </div>
    </div>
  );
};
