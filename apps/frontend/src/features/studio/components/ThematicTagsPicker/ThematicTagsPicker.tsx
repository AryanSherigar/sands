import React from "react";
import {
  MAX_THEMATIC_TAGS,
  THEMATIC_TAGS,
} from "@/shared/constants/thematic-tags";
import type { ThematicTagsPickerProps } from "./ThematicTagsPicker.types";

export const ThematicTagsPicker: React.FC<ThematicTagsPickerProps> = ({
  selected,
  onChange,
}) => {
  const isAtLimit = selected.length >= MAX_THEMATIC_TAGS;

  const handleToggle = (tagId: string): void => {
    if (selected.includes(tagId)) {
      onChange(selected.filter((id) => id !== tagId));
      return;
    }
    if (isAtLimit) return;
    onChange([...selected, tagId]);
  };

  return (
    <div className="space-y-2">
      <p className="text-xs text-content-faint">
        Optional. Shown on your story&apos;s page.{" "}
        <span className="font-mono">
          {selected.length} / {MAX_THEMATIC_TAGS}
        </span>
      </p>
      <div className="flex flex-wrap gap-2" role="group" aria-label="Themes">
        {THEMATIC_TAGS.map(({ id, label, explanation }) => {
          const isSelected = selected.includes(id);
          return (
            <button
              key={id}
              type="button"
              title={explanation}
              aria-pressed={isSelected}
              disabled={!isSelected && isAtLimit}
              onClick={() => handleToggle(id)}
              className={`rounded-md border px-3 py-1.5 font-sans text-xs transition-colors disabled:cursor-not-allowed disabled:opacity-40 ${
                isSelected
                  ? "border-content bg-content font-semibold text-surface"
                  : "border-border-subtle bg-surface-inset text-content-muted hover:border-border-strong hover:text-content"
              }`}
            >
              {label}
            </button>
          );
        })}
      </div>
    </div>
  );
};
