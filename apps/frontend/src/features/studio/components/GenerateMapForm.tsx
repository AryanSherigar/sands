import React, { useState } from "react";
import { Button } from "@/shared/components/ui/Button";
import type { GenerateMapFormProps } from "./GenerateMapForm.types";

const MIN_DESCRIPTION_CHARS = 3;
const MAX_DESCRIPTION_CHARS = 500;

export const GenerateMapForm: React.FC<GenerateMapFormProps> = ({
  initialDescription,
  isBusy,
  stageLabel,
  errorMessage,
  onGenerate,
}) => {
  const [description, setDescription] = useState(initialDescription);
  const trimmed = description.trim();
  const canGenerate = trimmed.length >= MIN_DESCRIPTION_CHARS && !isBusy;

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>): void => {
    event.preventDefault();
    if (canGenerate) onGenerate(trimmed);
  };

  return (
    <form className="space-y-3 text-sm" onSubmit={handleSubmit}>
      <label className="block space-y-1">
        Describe your world
        <textarea
          className="block w-full rounded-md border border-border bg-surface p-2"
          rows={3}
          maxLength={MAX_DESCRIPTION_CHARS}
          value={description}
          disabled={isBusy}
          onChange={(event) => setDescription(event.target.value)}
        />
      </label>
      <Button type="submit" disabled={!canGenerate}>
        Generate map
      </Button>
      {stageLabel && <p className="text-content-muted">{stageLabel}…</p>}
      {errorMessage && (
        <p role="alert" className="text-danger">
          {errorMessage}
        </p>
      )}
    </form>
  );
};
