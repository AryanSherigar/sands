import React, { useState } from "react";
import { IconX } from "@tabler/icons-react";
import { CARD_DEFAULT_NAME_LABEL } from "../../constants/card";
import type { TriggerChipsProps } from "./Card.types";

export const TriggerChips: React.FC<TriggerChipsProps> = ({
  name,
  triggers,
  onAdd,
  onRemove,
}) => {
  const [value, setValue] = useState("");

  const handleChange = (event: React.ChangeEvent<HTMLInputElement>): void =>
    setValue(event.target.value);
  const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>): void => {
    if (event.key !== "Enter") return;
    event.preventDefault();
    onAdd(value);
    setValue("");
  };

  return (
    <div className="space-y-2">
      <span className="block text-meta font-medium text-content-muted">Triggers</span>
      <div className="flex flex-wrap items-center gap-2">
        {triggers.map((trigger) => (
          <span
            key={trigger}
            className="flex items-center gap-1 rounded-sm border border-border-strong bg-surface-inset px-2 py-1 text-micro text-content"
          >
            <span>{trigger}</span>
            <button
              type="button"
              aria-label={`Remove trigger ${trigger}`}
              onClick={() => onRemove(trigger)}
              className="text-content-muted hover:text-danger"
            >
              <IconX size={12} aria-hidden="true" />
            </button>
          </span>
        ))}
        <input
          type="text"
          value={value}
          aria-label="Add a trigger"
          placeholder="Add a trigger"
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          className="min-w-32 flex-1 rounded-sm border border-border-subtle bg-surface-inset px-2 py-1 text-micro text-content placeholder:text-content-faint focus:border-primary focus:outline-hidden"
        />
      </div>
      <p className="text-micro text-content-faint">
        Words that bring {name.trim() || CARD_DEFAULT_NAME_LABEL} into the scene.
      </p>
    </div>
  );
};
