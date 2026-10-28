import React from "react";
import { IconCheck, IconCircle, IconX } from "@tabler/icons-react";
import {
  SUGGESTION_HINTS,
  type ChecklistItem,
  type RequiredItemId,
  type SuggestionId,
} from "../../lib/finishChecklist";
import type { FinishChecklistProps } from "./Guide.types";

const FixButton: React.FC<{ item: ChecklistItem<string>; onFix: (step: number) => void }> = ({
  item,
  onFix,
}) => (
  <button
    type="button"
    aria-label={`Fix ${item.label}`}
    onClick={() => onFix(item.fixStep)}
    className="text-meta text-content-muted underline underline-offset-4 hover:text-content"
  >
    Fix
  </button>
);

const RequiredRow: React.FC<{
  item: ChecklistItem<RequiredItemId>;
  onFix: (step: number) => void;
}> = ({ item, onFix }) => (
  <li className="flex items-center gap-2 text-body text-content">
    {item.isDone ? (
      <IconCheck size={16} aria-hidden="true" className="text-success" />
    ) : (
      <IconX size={16} aria-hidden="true" className="text-danger" />
    )}
    <span>{item.label}</span>
    <span className="sr-only">{item.isDone ? "done" : "missing"}</span>
    {!item.isDone && <FixButton item={item} onFix={onFix} />}
  </li>
);

const SuggestionRow: React.FC<{
  item: ChecklistItem<SuggestionId>;
  onFix: (step: number) => void;
}> = ({ item, onFix }) => (
  <li className="flex items-center gap-2 text-meta text-content-muted">
    {item.isDone ? (
      <IconCheck size={14} aria-hidden="true" className="text-success" />
    ) : (
      <IconCircle size={14} aria-hidden="true" />
    )}
    <span>
      {item.label}
      {!item.isDone && ` — ${SUGGESTION_HINTS[item.id]}`}
    </span>
    {!item.isDone && <FixButton item={item} onFix={onFix} />}
  </li>
);

export const FinishChecklist: React.FC<FinishChecklistProps> = ({
  requiredItems,
  suggestions,
  onFix,
}) => (
  <section aria-label="Checklist" className="space-y-3">
    <ul aria-label="Required" className="space-y-1.5">
      {requiredItems.map((item) => (
        <RequiredRow key={item.id} item={item} onFix={onFix} />
      ))}
    </ul>
    <ul aria-label="Suggestions" className="space-y-1">
      {suggestions.map((item) => (
        <SuggestionRow key={item.id} item={item} onFix={onFix} />
      ))}
    </ul>
  </section>
);
