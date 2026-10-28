import React from "react";
import { IconAlertCircle, IconChevronDown } from "@tabler/icons-react";
import { NormalizedSetupField } from "./SetupStageCard.types";
import { getStringValue, getArrayValue } from "./setupStageUtils";

interface SetupFieldRendererProps {
  field: NormalizedSetupField;
  value: unknown;
  error?: string;
  onChange: (fieldKey: string, value: unknown) => void;
  onMultiSelectToggle: (fieldKey: string, optionValue: string) => void;
}

const FieldLabel: React.FC<{ field: NormalizedSetupField }> = ({ field }) => (
  <label className="block font-mono text-xs uppercase tracking-wider text-content font-semibold transition-colors">
    {field.label}{" "}
    {field.is_character_name && (
      <span className="text-[10px] text-content-muted bg-surface-inset px-1.5 py-0.5 rounded-sm border border-border-subtle ml-1 font-mono uppercase">
        PROTAGONIST
      </span>
    )}
    {field.required && <span className="text-danger font-bold ml-1">*</span>}
  </label>
);

const SelectInput: React.FC<{
  field: NormalizedSetupField;
  value: unknown;
  onChange: (value: string) => void;
}> = ({ field, value, onChange }) => (
  <div className="relative">
    <select
      value={getStringValue(value)}
      onChange={(e) => onChange(e.target.value)}
      className="w-full h-10 bg-surface-inset border border-border-strong px-3 text-sm text-content font-mono rounded-sm appearance-none focus:outline-hidden focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all cursor-pointer"
    >
      <option value="" disabled>
        Select option...
      </option>
      {field.options.map((opt) => (
        <option key={opt.id} value={opt.value}>
          {opt.label}
        </option>
      ))}
    </select>
    <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-content-muted">
      <IconChevronDown size={16} stroke={1.5} aria-hidden="true" />
    </div>
  </div>
);

const MultiSelectInput: React.FC<{
  field: NormalizedSetupField;
  value: unknown;
  onToggle: (optionValue: string) => void;
}> = ({ field, value, onToggle }) => (
  <div className="space-y-2 bg-surface-inset border border-border-strong p-3 rounded-sm">
    {field.options.map((opt) => {
      const isChecked = getArrayValue(value).includes(opt.value);
      return (
        <label
          key={opt.id}
          className="flex items-center gap-3 text-xs font-mono text-content-muted cursor-pointer hover:text-content transition-colors py-1"
        >
          <input
            type="checkbox"
            checked={isChecked}
            onChange={() => onToggle(opt.value)}
            className="w-4 h-4 rounded-sm border-border-strong bg-surface-sunken text-primary focus:ring-primary/20 accent-primary"
          />
          {opt.label}
        </label>
      );
    })}
  </div>
);

export const SetupFieldRenderer: React.FC<SetupFieldRendererProps> = ({
  field,
  value,
  error,
  onChange,
  onMultiSelectToggle,
}) => {
  const isSelect = field.type === "single_select" || field.type === "select";

  return (
    <div className="space-y-2 group">
      <FieldLabel field={field} />
      {field.description && (
        <p className="font-sans text-xs text-content-muted">{field.description}</p>
      )}

      {isSelect && (
        <SelectInput
          field={field}
          value={value}
          onChange={(val) => onChange(field.key, val)}
        />
      )}

      {field.type === "multi_select" && (
        <MultiSelectInput
          field={field}
          value={value}
          onToggle={(val) => onMultiSelectToggle(field.key, val)}
        />
      )}

      {field.type === "text" && (
        <input
          type="text"
          value={getStringValue(value)}
          onChange={(e) => onChange(field.key, e.target.value)}
          placeholder={field.placeholder || "Enter text..."}
          className="w-full h-10 bg-surface-inset border border-border-strong px-3 text-sm text-content font-mono rounded-sm placeholder:text-content-faint focus:outline-hidden focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all"
        />
      )}

      {field.type === "textarea" && (
        <textarea
          rows={3}
          value={getStringValue(value)}
          onChange={(e) => onChange(field.key, e.target.value)}
          placeholder={field.placeholder || "Enter details..."}
          className="w-full bg-surface-inset border border-border-strong p-3 text-sm text-content font-mono rounded-sm placeholder:text-content-faint focus:outline-hidden focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all resize-none"
        />
      )}

      {field.type === "number" && (
        <input
          type="number"
          value={getStringValue(value)}
          onChange={(e) =>
            onChange(field.key, e.target.valueAsNumber || e.target.value)
          }
          placeholder={field.placeholder}
          className="w-full h-10 bg-surface-inset border border-border-strong px-3 text-sm text-content font-mono rounded-sm placeholder:text-content-faint focus:outline-hidden focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all"
        />
      )}

      {error && (
        <p className="font-mono text-xs text-danger mt-1 flex items-center gap-1.5">
          <IconAlertCircle size={14} stroke={1.5} aria-hidden="true" />
          <span>{error}</span>
        </p>
      )}
    </div>
  );
};
