import React from "react";
import {
  CONTENT_TAGS,
  CONTENT_TAG_LABELS,
} from "@/shared/constants/content-tags";
import type { ContentTagPickerProps } from "./ContentTagPicker.types";

const DEFAULT_LABEL = "Content Tag *";
const DEFAULT_DESCRIPTION =
  "Declare the content level for this scenario. Checked at publish time.";

export const ContentTagPicker: React.FC<ContentTagPickerProps> = ({
  value,
  onChange,
  disabled,
  label = DEFAULT_LABEL,
  description = DEFAULT_DESCRIPTION,
}) => {
  return (
    <div className="space-y-3">
      <label className="block text-sm font-semibold tracking-wide text-content-muted uppercase">
        {label}
      </label>
      <p className="text-xs text-content-faint">{description}</p>
      <div className="flex flex-wrap gap-2">
        {CONTENT_TAGS.map((tag) => {
          const isSelected = value === tag;
          return (
            <button
              key={tag}
              type="button"
              disabled={disabled}
              onClick={() => onChange(tag)}
              className={`rounded-md px-3 py-1 text-xs font-mono border transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
                isSelected
                  ? "bg-content text-surface border-content font-semibold"
                  : "bg-surface-inset text-content-muted border-border-subtle hover:border-border-strong hover:text-content"
              }`}
            >
              {CONTENT_TAG_LABELS[tag]}
            </button>
          );
        })}
      </div>
    </div>
  );
};
