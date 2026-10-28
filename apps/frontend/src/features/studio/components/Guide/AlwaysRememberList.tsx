import React from "react";
import { IconX } from "@tabler/icons-react";
import { ALWAYS_REMEMBER_SECTION_ID } from "../../constants/advancedCards";
import {
  ALWAYS_REMEMBER_MAX_LINE_LENGTH,
  ALWAYS_REMEMBER_MAX_LINES,
  ALWAYS_REMEMBER_SOFT_LIMIT,
} from "../../constants/guideLimits";
import { useAlwaysRemember } from "../../hooks/useAlwaysRemember";

const NUDGE_COPY = "Keep the list short — the narrator reads this every turn.";

export const AlwaysRememberList: React.FC = () => {
  const { lines, canAdd, addLine, editLine, removeLine } = useAlwaysRemember();
  const isOverSoftLimit = lines.length >= ALWAYS_REMEMBER_SOFT_LIMIT;

  return (
    <section aria-labelledby={ALWAYS_REMEMBER_SECTION_ID} className="space-y-3">
      <div className="space-y-1">
        <h3 id={ALWAYS_REMEMBER_SECTION_ID} className="text-heading font-semibold text-content">
          Always remember
        </h3>
        <p className="text-meta text-content-muted">
          Things the narrator must never forget or break. Keep each one short.
        </p>
      </div>
      <ul className="space-y-2">
        {lines.map((line, index) => (
          <li key={index} className="flex items-center gap-2">
            <input
              type="text"
              aria-label={`Always remember ${index + 1}`}
              value={line}
              maxLength={ALWAYS_REMEMBER_MAX_LINE_LENGTH}
              onChange={(event) => editLine(index, event.target.value)}
              className="h-10 flex-1 rounded-sm border border-border-strong bg-surface-inset px-3 text-body text-content focus:border-primary focus:outline-hidden"
            />
            <button
              type="button"
              aria-label={`Remove line ${index + 1}`}
              onClick={() => removeLine(index)}
              className="flex h-8 w-8 items-center justify-center rounded-md text-content-muted hover:bg-white/6 hover:text-content"
            >
              <IconX size={16} aria-hidden="true" />
            </button>
          </li>
        ))}
      </ul>
      <div className="flex items-center justify-between gap-4">
        <button
          type="button"
          disabled={!canAdd}
          onClick={() => addLine("")}
          className="text-meta font-medium text-content-muted underline underline-offset-4 hover:text-content disabled:no-underline disabled:opacity-40"
        >
          + Add
        </button>
        <span className="text-micro text-content-faint">
          {lines.length} of {ALWAYS_REMEMBER_SOFT_LIMIT}
        </span>
      </div>
      {isOverSoftLimit && canAdd && <p className="text-micro text-warning">{NUDGE_COPY}</p>}
      {!canAdd && (
        <p className="text-micro text-danger">
          The narrator can hold up to {ALWAYS_REMEMBER_MAX_LINES} lines. Remove one to add another.
        </p>
      )}
    </section>
  );
};
