import React, { useId, useState } from "react";
import { Button } from "@/shared/components/ui/Button";
import { Select } from "@/shared/components/ui/Select";
import {
  LINK_TARGET_CARD,
  LINK_TARGET_OPTIONS,
  LINK_TARGET_TEXT,
  LINK_TEXT_LABEL,
  LINK_TEXT_PLACEHOLDER,
} from "../../constants/cardValues";
import { getLinkSuggestions } from "../../lib/cardLinks";
import { getCardKind } from "../../lib/cardKind";
import type { NewLinkInput } from "../../types/fact.types";
import type { AddLinkFormProps } from "./Links.types";
import { LinkWhenField } from "./LinkWhenField";

type TargetKind = typeof LINK_TARGET_CARD | typeof LINK_TARGET_TEXT;

const buildInput = (
  predicate: string,
  targetKind: TargetKind,
  otherEntityId: string,
  text: string,
  whenActive: Record<string, unknown> | null,
): NewLinkInput => ({
  predicate: predicate.trim(),
  ...(targetKind === LINK_TARGET_CARD ? { otherEntityId } : { objectLiteral: text.trim() }),
  ...(whenActive ? { whenActive } : {}),
});

export const AddLinkForm: React.FC<AddLinkFormProps> = ({
  subjectName,
  subjectKind,
  candidates,
  isAdvanced = false,
  onSubmit,
  onCancel,
}) => {
  const kindId = useId();
  const targetId = useId();
  const textId = useId();
  const predicateId = useId();
  const listId = useId();
  const [targetKind, setTargetKind] = useState<TargetKind>(LINK_TARGET_CARD);
  const [otherEntityId, setOtherEntityId] = useState("");
  const [text, setText] = useState("");
  const [predicate, setPredicate] = useState("");
  const [whenActive, setWhenActive] = useState<Record<string, unknown> | null>(null);
  const target = candidates.find((entity) => entity.entity_id === otherEntityId);
  const suggestions = getLinkSuggestions(
    subjectKind,
    target ? getCardKind(target.entity_type) : "other",
  );
  const isTextTarget = isAdvanced && targetKind === LINK_TARGET_TEXT;
  const hasFarEnd = isTextTarget ? text.trim().length > 0 : Boolean(target);
  const canSave = hasFarEnd && predicate.trim().length > 0;

  const handleKindChange = (event: React.ChangeEvent<HTMLSelectElement>): void =>
    setTargetKind(event.target.value as TargetKind);
  const handleTargetChange = (event: React.ChangeEvent<HTMLSelectElement>): void =>
    setOtherEntityId(event.target.value);
  const handleTextChange = (event: React.ChangeEvent<HTMLInputElement>): void =>
    setText(event.target.value);
  const handlePredicateChange = (
    event: React.ChangeEvent<HTMLInputElement>,
  ): void => setPredicate(event.target.value);
  const handleSubmit = (event: React.FormEvent): void => {
    event.preventDefault();
    if (!canSave) return;
    const effectiveKind = isTextTarget ? LINK_TARGET_TEXT : LINK_TARGET_CARD;
    onSubmit(buildInput(predicate, effectiveKind, otherEntityId, text, whenActive));
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-3 rounded-md border border-border-subtle bg-surface-inset p-3"
    >
      {isAdvanced && (
        <div className="space-y-1">
          <label htmlFor={kindId} className="block text-meta text-content-muted">
            Link to a
          </label>
          <Select
            id={kindId}
            value={targetKind}
            onChange={handleKindChange}
            options={[...LINK_TARGET_OPTIONS]}
          />
        </div>
      )}
      {isTextTarget ? (
        <div className="space-y-1">
          <label htmlFor={textId} className="block text-meta text-content-muted">
            {LINK_TEXT_LABEL}
          </label>
          <input
            id={textId}
            type="text"
            value={text}
            onChange={handleTextChange}
            placeholder={LINK_TEXT_PLACEHOLDER}
            className="w-full rounded-sm border border-border-strong bg-surface px-3 py-2 text-sm text-content placeholder:text-content-faint focus:border-primary focus:outline-hidden"
          />
        </div>
      ) : (
        <div className="space-y-1">
          <label htmlFor={targetId} className="block text-meta text-content-muted">
            Link to
          </label>
          <Select
            id={targetId}
            value={otherEntityId}
            onChange={handleTargetChange}
            options={[
              { value: "", label: "Choose a card…" },
              ...candidates.map((entity) => ({
                value: entity.entity_id,
                label: entity.canonical_name,
              })),
            ]}
          />
        </div>
      )}
      <div className="space-y-1">
        <label htmlFor={predicateId} className="block text-meta text-content-muted">
          How are they linked?
        </label>
        <input
          id={predicateId}
          type="text"
          list={listId}
          value={predicate}
          onChange={handlePredicateChange}
          placeholder={`${subjectName} …`}
          className="w-full rounded-sm border border-border-strong bg-surface px-3 py-2 text-sm text-content placeholder:text-content-faint focus:border-primary focus:outline-hidden"
        />
        <datalist id={listId}>
          {suggestions.map((suggestion) => (
            <option key={suggestion} value={suggestion} />
          ))}
        </datalist>
      </div>
      {isAdvanced && <LinkWhenField whenActive={whenActive} onChange={setWhenActive} />}
      <div className="flex gap-2">
        <Button type="submit" size="sm" disabled={!canSave}>
          Save link
        </Button>
        <Button type="button" size="sm" variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
      </div>
    </form>
  );
};
