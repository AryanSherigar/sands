import React, { useState } from "react";
import { Input } from "@/shared/components/ui/Input";
import { Select } from "@/shared/components/ui/Select";
import { readChoices, setOptions } from "../../../lib/trackedValueEditing";
import type { TrackedValueFieldsProps } from "./Advanced.types";

const splitChoices = (raw: string): string[] =>
  raw
    .split(",")
    .map((choice) => choice.trim())
    .filter(Boolean);

export const ChoicesField: React.FC<TrackedValueFieldsProps> = ({ field, onChange }) => {
  const [text, setText] = useState(readChoices(field).join(", "));
  const choices = readChoices(field);

  const handleChoicesChange = (event: React.ChangeEvent<HTMLInputElement>): void => {
    setText(event.target.value);
    const next = splitChoices(event.target.value);
    if (next.length > 0) onChange(setOptions(field, next));
  };

  return (
    <div className="grid grid-cols-2 gap-3">
      <label className="block space-y-1 text-meta text-content-muted">
        Choices
        <Input value={text} placeholder="Dawn, Day, Dusk, Night" onChange={handleChoicesChange} />
      </label>
      <label className="block space-y-1 text-meta text-content-muted">
        Starts as
        <Select
          value={typeof field.initial === "string" ? field.initial : ""}
          options={choices.map((choice) => ({ value: choice, label: choice }))}
          onChange={(event) => onChange({ ...field, initial: event.target.value })}
        />
      </label>
    </div>
  );
};
