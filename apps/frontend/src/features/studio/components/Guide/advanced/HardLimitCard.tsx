import React, { useMemo, useState } from "react";
import { Select } from "@/shared/components/ui/Select";
import type { OverflowMenuItem } from "@/shared/components/ui/OverflowMenu.types";
import { DELETE_LABEL, DUPLICATE_LABEL, MISSING_VALUE_BLOCK_MESSAGE } from "../../../constants/advancedCards";
import {
  APPLIES_TO_EVERYONE,
  APPLIES_TO_PLAYER,
  IN_WORDS_HELPER,
  IN_WORDS_LABEL,
  SAY_IT_IN_WORDS_MESSAGE,
  LIMIT_KIND_OPTIONS,
  type LimitKind,
} from "../../../constants/hardLimits";
import { useGuideCards } from "../../../hooks/useGuideCards";
import { useOpenFullEditor } from "../../../hooks/useOpenFullEditor";
import { useRowAutosave } from "../../../hooks/useRowAutosave";
import { useValueOptions } from "../../../hooks/useValueOptions";
import {
  buildLimitDraft,
  buildLimitPatch,
  buildScopeFilter,
  buildSuggestedText,
  findRedundantBoundMessage,
  inferLimitKind,
  listAppliesToCards,
  readEffectiveText,
  type LimitDraft,
} from "../../../lib/limitDraft";
import { buildLabelMap } from "../../../lib/ruleDraft";
import { SentenceBuilder } from "../../SentenceBuilder/SentenceBuilder";
import type { HardLimitCardProps } from "./Advanced.types";
import { AdvancedCard } from "./AdvancedCard";
import { ComparisonFitNote } from "./ComparisonFitNote";
import { FieldBlock } from "./FieldBlock";

export const HardLimitCard: React.FC<HardLimitCardProps> = ({ limit, index, onUpdate, onDuplicate, onDelete }) => {
  const options = useValueOptions();
  const { entities } = useGuideCards();
  const openFullEditor = useOpenFullEditor();
  const [isValid, setIsValid] = useState(true);
  const [hasEditedText, setHasEditedText] = useState(false);
  const labels = useMemo(() => buildLabelMap(options), [options]);
  const serverDraft = useMemo(() => buildLimitDraft(limit, labels), [labels, limit]);
  const [kind, setKind] = useState<LimitKind>(() => inferLimitKind(serverDraft.expression));
  const { value: draft, commit } = useRowAutosave<LimitDraft>({
    serverDraft,
    save: (next) => {
      if (readEffectiveText(next, labels) === "") return;
      const patch = buildLimitPatch(limit, next, labels, !isValid);
      if (Object.keys(patch).length > 0) onUpdate(patch);
    },
  });
  const suggestedText = buildSuggestedText(draft, labels);
  const isTextMissing = readEffectiveText(draft, labels) === "" && (hasEditedText || draft.expression !== null);
  const label = `Hard limit ${index + 1}`;
  const scopeFilter = useMemo(
    () => buildScopeFilter(draft.appliesTo, entities, draft.expression),
    [draft.appliesTo, draft.expression, entities],
  );
  const redundantMessage = kind === "compare" ? findRedundantBoundMessage(draft, options) : null;
  const appliesToOptions = [
    { value: APPLIES_TO_PLAYER, label: "The player" },
    { value: APPLIES_TO_EVERYONE, label: "Everyone" },
    ...listAppliesToCards(entities, draft.appliesTo).map((entity) => ({ value: entity.entity_id, label: entity.canonical_name })),
  ];
  const menuItems: OverflowMenuItem[] = [
    { id: "duplicate", label: DUPLICATE_LABEL, onSelect: onDuplicate },
    { id: "delete", label: DELETE_LABEL, isDanger: true, onSelect: onDelete },
  ];

  const handleTextChange = (event: React.ChangeEvent<HTMLTextAreaElement>): void => {
    setHasEditedText(true);
    commit({ ...draft, text: event.target.value });
  };
  const handleKindChange = (next: LimitKind): void => {
    if (next === kind) return;
    setKind(next);
    commit({ ...draft, expression: null, metadata: undefined });
  };

  return (
    <AdvancedCard ariaLabel={label} badge={label} menuLabel={`${label} options`} menuItems={menuItems}>
      <fieldset className="space-y-1.5">
        <legend className="text-meta font-medium text-content-muted">Kind</legend>
        <div className="flex flex-wrap gap-4">
          {LIMIT_KIND_OPTIONS.map((option) => (
            <label key={option.value} className="flex items-center gap-2 text-body text-content">
              <input
                type="radio"
                name={`${limit.invariant_id}-kind`}
                checked={kind === option.value}
                onChange={() => handleKindChange(option.value)}
              />
              {option.label}
            </label>
          ))}
        </div>
      </fieldset>
      <FieldBlock label={kind === "compare" ? "Always" : "While"}>
        <SentenceBuilder
          key={kind}
          value={draft.expression}
          metadata={draft.metadata}
          mode={kind === "compare" ? "condition" : "while-limit"}
          canCompareToValue={kind === "compare"}
          maxRows={kind === "compare" ? 1 : undefined}
          scopeFilter={scopeFilter}
          onChange={(next) => commit({ ...draft, expression: next?.expression ?? null, metadata: next?.metadata })}
          onOpenFullEditor={openFullEditor}
          onValidityChange={setIsValid}
        />
        {!isValid && <p className="text-meta text-danger">{MISSING_VALUE_BLOCK_MESSAGE}</p>}
        <ComparisonFitNote expression={draft.expression} metadata={draft.metadata} options={options} />
        {redundantMessage && <p className="text-meta text-warning">{redundantMessage}</p>}
      </FieldBlock>
      <label className="block max-w-64 space-y-1 text-meta font-medium text-content-muted">
        Applies to
        <Select
          value={draft.appliesTo}
          options={appliesToOptions}
          onChange={(event) => commit({ ...draft, appliesTo: event.target.value })}
        />
      </label>
      <FieldBlock label={`${IN_WORDS_LABEL} (required)`} helper={IN_WORDS_HELPER}>
        <textarea
          aria-label={IN_WORDS_LABEL}
          aria-required="true"
          value={hasEditedText ? draft.text : draft.text || suggestedText}
          placeholder={suggestedText}
          rows={2}
          onChange={handleTextChange}
          className="w-full resize-y rounded-sm border border-border-strong bg-surface-inset px-3 py-2 text-body text-content placeholder:text-content-faint focus:border-primary focus:outline-hidden"
        />
        {isTextMissing && (
          <p role="alert" className="text-meta text-danger">
            {SAY_IT_IN_WORDS_MESSAGE}
          </p>
        )}
      </FieldBlock>
    </AdvancedCard>
  );
};
