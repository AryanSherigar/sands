import React, { useId } from "react";
import { IconLock, IconX } from "@tabler/icons-react";
import { cn } from "@/shared/lib/cn";
import type { LinkRowProps } from "./Links.types";
import { LinkWhenField } from "./LinkWhenField";

const MISSING_CARD_NAME = "Missing card";

export const LinkRow: React.FC<LinkRowProps> = ({
  view,
  currentEntityId,
  suggestions,
  isAdvanced = false,
  onChangeWhen,
  onChangePredicate,
  onToggleSecret,
  onDelete,
  onOpenCard,
}) => {
  const listId = useId();
  const { fact, subject, object } = view;
  const subjectName = subject?.canonical_name ?? MISSING_CARD_NAME;
  const objectName = object?.canonical_name ?? fact.object_literal ?? MISSING_CARD_NAME;

  const renderName = (name: string, entityId: string | undefined) => {
    if (!entityId || entityId === currentEntityId || !onOpenCard) {
      return <span className="text-meta font-medium text-content">{name}</span>;
    }
    return (
      <button
        type="button"
        aria-label={`Open ${name}`}
        onClick={() => onOpenCard(entityId)}
        className="text-meta font-medium text-content underline underline-offset-2 hover:text-content-muted"
      >
        {name}
      </button>
    );
  };

  const handleBlur = (event: React.FocusEvent<HTMLInputElement>): void => {
    const next = event.target.value.trim();
    if (next && next !== fact.predicate) onChangePredicate(fact, next);
  };
  const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>): void => {
    if (event.key === "Enter") event.currentTarget.blur();
  };
  const handleSecretClick = (): void => onToggleSecret(fact, !fact.hidden);
  const handleDeleteClick = (): void => onDelete(fact);

  return (
    <li className="flex flex-wrap items-center gap-2 rounded-md border border-border-subtle bg-surface-inset px-3 py-2">
      {renderName(subjectName, fact.subject_entity_id)}
      <input
        key={fact.predicate}
        type="text"
        list={listId}
        defaultValue={fact.predicate}
        aria-label={`How ${subjectName} and ${objectName} are linked`}
        onBlur={handleBlur}
        onKeyDown={handleKeyDown}
        className="min-w-32 flex-1 rounded-sm border border-border-strong bg-surface px-2 py-1 text-meta text-content focus:border-primary focus:outline-hidden"
      />
      <datalist id={listId}>
        {suggestions.map((suggestion) => (
          <option key={suggestion} value={suggestion} />
        ))}
      </datalist>
      {renderName(objectName, fact.object_entity_id ?? undefined)}
      <button
        type="button"
        aria-pressed={fact.hidden}
        aria-label="Secret"
        onClick={handleSecretClick}
        className={cn(
          "flex items-center gap-1 rounded-sm border px-2 py-1 text-micro",
          fact.hidden
            ? "border-primary bg-primary text-primary-contrast"
            : "border-border-strong text-content-muted hover:text-content",
        )}
      >
        <IconLock size={12} aria-hidden="true" />
        Secret
      </button>
      <button
        type="button"
        aria-label={`Remove link between ${subjectName} and ${objectName}`}
        onClick={handleDeleteClick}
        className="rounded-sm p-1 text-content-muted hover:text-danger"
      >
        <IconX size={14} aria-hidden="true" />
      </button>
      {isAdvanced && onChangeWhen && (
        <LinkWhenField
          whenActive={fact.when_active}
          onChange={(next) => onChangeWhen(fact, next)}
        />
      )}
    </li>
  );
};
