import React, { useId } from "react";
import { IconTrash } from "@tabler/icons-react";
import { Input } from "@/shared/components/ui/Input";
import { Select } from "@/shared/components/ui/Select";
import { SETUP_FIELD_TYPE_OPTIONS } from "../../constants/guideChips";
import { addOption, renameOption } from "../../lib/setupFields";
import type { SetupInputType } from "@/shared/types/scenario.types";
import type { SetupFieldRowProps } from "./Guide.types";

const isPickType = (type: SetupInputType): boolean =>
  type === "single_select" || type === "multi_select";

export const SetupFieldRow: React.FC<SetupFieldRowProps> = ({
  field,
  onChange,
  onRemove,
}) => {
  const labelId = useId();

  const handleTypeChange = (event: React.ChangeEvent<HTMLSelectElement>): void =>
    onChange({ type: event.target.value as SetupInputType });

  return (
    <li className="space-y-3 rounded-md border border-border-subtle bg-surface-raised p-3">
      <div className="flex items-center gap-2">
        <div className="flex-1">
          <Input
            id={labelId}
            aria-label="Question label"
            placeholder="What should players be asked?"
            value={field.label}
            onChange={(event) => onChange({ label: event.target.value })}
          />
        </div>
        <div className="w-40">
          <Select
            aria-label={`Answer type for ${field.label || "this question"}`}
            options={SETUP_FIELD_TYPE_OPTIONS}
            value={field.type}
            onChange={handleTypeChange}
          />
        </div>
        <button
          type="button"
          aria-label={`Remove ${field.label || "this question"}`}
          onClick={onRemove}
          className="flex h-8 w-8 items-center justify-center rounded-md text-content-muted hover:bg-white/6 hover:text-danger"
        >
          <IconTrash size={16} aria-hidden="true" />
        </button>
      </div>
      {isPickType(field.type) && (
        <ul className="space-y-2">
          {field.options.map((option) => (
            <li key={option.id}>
              <Input
                aria-label={`Choice for ${field.label || "this question"}`}
                value={option.label}
                onChange={(event) =>
                  onChange({ options: renameOption(field.options, option.id, event.target.value) })
                }
              />
            </li>
          ))}
          <li>
            <button
              type="button"
              onClick={() => onChange({ options: addOption(field) })}
              className="text-meta text-content-muted underline underline-offset-4 hover:text-content"
            >
              + Add a choice
            </button>
          </li>
        </ul>
      )}
      <label className="flex items-center gap-2 text-meta text-content-muted">
        <input
          type="checkbox"
          checked={field.required}
          onChange={(event) => onChange({ required: event.target.checked })}
          className="accent-primary"
        />
        Players must answer
      </label>
    </li>
  );
};
