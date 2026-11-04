import { useState } from "react";
import { composeCardSentence, isRegionKind, isRegionTemplate, type ClauseDraft } from "../../../../lib/clauseSentence";
import { StrategyFormDialog } from "../../ui/StrategyFormDialog";
import { ClauseDraftFields } from "./ClauseDraftFields";
import type { ClauseBuilderDialogProps } from "./ClauseBuilderDialog.types";

export const MAX_CARD_CLAUSES = 4;

const NEW_DRAFT: ClauseDraft = {
  mode: "none",
  kind: "payment",
  amount: 50,
  template: "treasury_below",
  subject: "mine",
  value: 100,
  expiresInTurns: 10,
};

const isDraftComplete = (draft: ClauseDraft): boolean => {
  const needsRegion = isRegionKind(draft.kind) || (draft.mode !== "none" && isRegionTemplate(draft.template));
  return !needsRegion || Boolean(draft.regionId);
};

export function ClauseBuilderDialog({ regions = [], onUse, onCancel }: ClauseBuilderDialogProps) {
  const [drafts, setDrafts] = useState<ClauseDraft[]>([NEW_DRAFT]);
  const updateAt = (index: number, change: Partial<ClauseDraft>): void =>
    setDrafts((current) => current.map((draft, position) => (position === index ? { ...draft, ...change } : draft)));
  const removeAt = (index: number): void => setDrafts((current) => current.filter((_, position) => position !== index));
  const handleAdd = (): void => setDrafts((current) => [...current, NEW_DRAFT]);
  const canSubmit = drafts.every(isDraftComplete);

  return (
    <StrategyFormDialog
      title="Draft a proposal"
      description="Build one or more clauses, each straight away or conditional. This writes a sentence for you to read and send. The ruler weighs it as a whole and decides."
      submitLabel="Use this sentence"
      isSubmitDisabled={!canSubmit}
      onSubmit={() => onUse(composeCardSentence(drafts))}
      onCancel={onCancel}
    >
      {drafts.map((draft, index) => (
        <ClauseDraftFields
          key={index}
          draft={draft}
          position={index + 1}
          regions={regions}
          canRemove={drafts.length > 1}
          onChange={(change) => updateAt(index, change)}
          onRemove={() => removeAt(index)}
        />
      ))}
      {drafts.length < MAX_CARD_CLAUSES ? (
        <button type="button" onClick={handleAdd} className="font-sans text-sm font-semibold text-primary hover:underline cursor-pointer">
          Add another clause
        </button>
      ) : null}
    </StrategyFormDialog>
  );
}
