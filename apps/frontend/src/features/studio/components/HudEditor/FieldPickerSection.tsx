import React from "react";
import { Button } from "@/shared/components/ui/Button";
import { Select } from "@/shared/components/ui/Select";
import { FieldPickerSectionProps } from "./FieldPickerSection.types";

export const FieldPickerSection: React.FC<FieldPickerSectionProps> = ({
  title,
  fieldLabel,
  fields,
  path,
  isPathLocked,
  problems,
  isSaving,
  onPathChange,
  onSave,
  onRemove,
  children,
}) => {
  const options = [
    { value: "", label: "Choose a tracked value" },
    ...fields.map((field) => ({
      value: field.path,
      label: `${field.label} (${field.path})`,
    })),
  ];
  const canSave = path !== "" && problems.length === 0 && !isSaving;

  return (
    <section
      aria-label={title}
      className="rounded-md space-y-3 border border-border-subtle p-3"
    >
      <h2 className="text-sm font-semibold text-content">{title}</h2>
      <Select
        aria-label={fieldLabel}
        options={options}
        value={path}
        disabled={isPathLocked}
        onChange={(event) => onPathChange(event.target.value)}
      />
      {fields.length === 0 && (
        <p className="text-xs text-warning">
          No suitable tracked value yet. Add one in Tracked Values first.
        </p>
      )}
      {children}
      {path !== "" && problems.length > 0 && (
        <ul role="alert" className="list-disc pl-5 text-xs text-warning">
          {problems.map((problem) => (
            <li key={problem}>{problem}</li>
          ))}
        </ul>
      )}
      <div className="flex gap-2">
        <Button type="button" size="sm" disabled={!canSave} onClick={onSave}>
          {`Save ${title.toLowerCase()}`}
        </Button>
        {onRemove && (
          <Button type="button" size="sm" variant="danger" onClick={onRemove}>
            {`Remove ${title.toLowerCase()}`}
          </Button>
        )}
      </div>
    </section>
  );
};
