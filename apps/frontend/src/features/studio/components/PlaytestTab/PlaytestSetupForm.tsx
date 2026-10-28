import React, { useState } from "react";
import { Button } from "@/shared/components/ui/Button";
import { Select } from "@/shared/components/ui/Select";
import {
  buildInitialSetupValues,
  getMissingRequiredFields,
} from "../../lib/playtestSetup";
import type { PlaytestSetupFormProps } from "./PlaytestTab.types";

const INPUT_CLASSES =
  "w-full rounded-sm border border-border-strong bg-surface-inset px-2 py-1.5 text-body text-content focus:border-primary focus:outline-hidden";

export const PlaytestSetupForm: React.FC<PlaytestSetupFormProps> = ({ fields, isStarting, onStart }) => {
  const [values, setValues] = useState(() => buildInitialSetupValues(fields));
  const missing = getMissingRequiredFields(fields, values);

  const handleChange = (key: string, value: unknown): void =>
    setValues((current) => ({ ...current, [key]: value }));
  const handleSubmit = (event: React.FormEvent): void => {
    event.preventDefault();
    if (missing.length === 0) onStart(values);
  };

  return (
    <form onSubmit={handleSubmit} className="mx-auto w-full max-w-[640px] space-y-4 px-4 py-8">
      <p className="text-body text-content-muted">Pick the choices a player would make, then start.</p>
      {fields.map((field) => (
        <div key={field.id} className="space-y-1">
          <label htmlFor={`playtest-${field.id}`} className="block text-meta font-medium text-content-muted">
            {field.label}
          </label>
          {field.type === "single_select" ? (
            <Select
              id={`playtest-${field.id}`}
              value={String(values[field.key] ?? "")}
              onChange={(event) => handleChange(field.key, event.target.value)}
              options={[
                { value: "", label: "Choose…" },
                ...field.options.map((option) => ({ value: option.value, label: option.label })),
              ]}
            />
          ) : (
            <input
              id={`playtest-${field.id}`}
              type={field.type === "number" ? "number" : "text"}
              value={String(values[field.key] ?? "")}
              onChange={(event) => handleChange(field.key, event.target.value)}
              className={INPUT_CLASSES}
            />
          )}
        </div>
      ))}
      <Button type="submit" disabled={isStarting || missing.length > 0}>
        Start playtest
      </Button>
    </form>
  );
};
