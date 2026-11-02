import { useState } from "react";
import {
  GATE_KINDS,
  KIND_LABELS,
  MAX_EXPIRY_TURNS,
  MIN_EXPIRY_TURNS,
  TEMPLATE_LABELS,
  composeClauseSentence,
  type ClauseDraft,
  type ClauseKind,
  type ClauseMode,
  type ClauseSubject,
  type ClauseTemplate,
} from "../../../../lib/clauseSentence";
import { FORM_INPUT_CLASS, FormField } from "../../ui/FormField";
import { StrategyFormDialog } from "../../ui/StrategyFormDialog";

export interface ClauseBuilderDialogProps {
  onUse: (sentence: string) => void;
  onCancel: () => void;
}

const INITIAL_DRAFT: ClauseDraft = {
  mode: "trigger",
  kind: "payment",
  amount: 50,
  template: "treasury_below",
  subject: "mine",
  value: 100,
  expiresInTurns: 10,
};

const NEEDS_AMOUNT: ClauseKind[] = ["payment", "tribute", "pact"];
const AMOUNT_LABELS: Partial<Record<ClauseKind, string>> = { payment: "Gold", tribute: "Percent of income", pact: "Turns" };

export function ClauseBuilderDialog({ onUse, onCancel }: ClauseBuilderDialogProps) {
  const [draft, setDraft] = useState<ClauseDraft>(INITIAL_DRAFT);
  const update = (change: Partial<ClauseDraft>): void => setDraft((current) => ({ ...current, ...change }));
  const availableKinds = (Object.keys(KIND_LABELS) as ClauseKind[]).filter(
    (kind) => draft.mode === "trigger" || GATE_KINDS.includes(kind),
  );

  const handleModeChange = (mode: ClauseMode): void => {
    const keepsKind = mode === "trigger" || GATE_KINDS.includes(draft.kind);
    update({ mode, kind: keepsKind ? draft.kind : "pact" });
  };

  return (
    <StrategyFormDialog
      title="Draft a conditional clause"
      description="This writes a sentence for you to read and send. The ruler decides whether to agree."
      submitLabel="Use this sentence"
      onSubmit={() => onUse(composeClauseSentence(draft))}
      onCancel={onCancel}
    >
      <FormField label="When it applies">
        <select className={FORM_INPUT_CLASS} value={draft.mode} onChange={(event) => handleModeChange(event.target.value as ClauseMode)}>
          <option value="trigger">Once a condition is met, it begins</option>
          <option value="gate">It holds only while a condition is true</option>
        </select>
      </FormField>
      <FormField label="The clause">
        <select className={FORM_INPUT_CLASS} value={draft.kind} onChange={(event) => update({ kind: event.target.value as ClauseKind })}>
          {availableKinds.map((kind) => (
            <option key={kind} value={kind}>{KIND_LABELS[kind]}</option>
          ))}
        </select>
      </FormField>
      {NEEDS_AMOUNT.includes(draft.kind) ? (
        <FormField label={AMOUNT_LABELS[draft.kind] ?? "Amount"}>
          <input className={FORM_INPUT_CLASS} type="number" min={1} value={draft.amount} onChange={(event) => update({ amount: Number(event.target.value) })} />
        </FormField>
      ) : null}
      <FormField label="Condition">
        <select className={FORM_INPUT_CLASS} value={draft.template} onChange={(event) => update({ template: event.target.value as ClauseTemplate })}>
          {(Object.keys(TEMPLATE_LABELS) as ClauseTemplate[]).map((template) => (
            <option key={template} value={template}>{TEMPLATE_LABELS[template]}</option>
          ))}
        </select>
      </FormField>
      {draft.template !== "turn_after" ? (
        <FormField label="Whose">
          <select className={FORM_INPUT_CLASS} value={draft.subject} onChange={(event) => update({ subject: event.target.value as ClauseSubject })}>
            <option value="mine">Mine</option>
            <option value="yours">Theirs</option>
          </select>
        </FormField>
      ) : null}
      <FormField label="Value">
        <input className={FORM_INPUT_CLASS} type="number" min={0} value={draft.value} onChange={(event) => update({ value: Number(event.target.value) })} />
      </FormField>
      <FormField label={`Lapses after (${MIN_EXPIRY_TURNS} to ${MAX_EXPIRY_TURNS} turns)`}>
        <input className={FORM_INPUT_CLASS} type="number" min={MIN_EXPIRY_TURNS} max={MAX_EXPIRY_TURNS} value={draft.expiresInTurns} onChange={(event) => update({ expiresInTurns: Number(event.target.value) })} />
      </FormField>
    </StrategyFormDialog>
  );
}
