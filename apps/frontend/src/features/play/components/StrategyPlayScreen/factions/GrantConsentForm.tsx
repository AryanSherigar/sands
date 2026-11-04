import { useState } from "react";
import { buildGrantConsentOrder } from "../../../lib/orderBuilders";
import type { FormOption } from "../../../lib/realmAffairs";
import type { ConsentActionKind, StrategyOrder } from "../../../types/simulation.types";
import { FORM_INPUT_CLASS, FormField } from "../ui/FormField";
import { StrategyFormDialog } from "../ui/StrategyFormDialog";

export interface GrantConsentFormProps {
  factionId: string;
  vassalageId: string;
  targets: FormOption[];
  onSubmit: (order: StrategyOrder) => void;
  onCancel: () => void;
}

const ACTION_LABELS: Record<ConsentActionKind, string> = {
  declare_war: "Declare war on them",
  demand: "Make demands of them",
  pact: "Sign a pact with them",
};

export function GrantConsentForm({ factionId, vassalageId, targets, onSubmit, onCancel }: GrantConsentFormProps) {
  const [action, setAction] = useState<ConsentActionKind>("declare_war");
  const [targetId, setTargetId] = useState(targets[0]?.id ?? "");

  return (
    <StrategyFormDialog
      title="Grant your vassal consent"
      description="Your vassal may act against another realm only with your leave. Consent is used once and lapses after a few turns."
      submitLabel="Grant consent"
      isSubmitDisabled={!targetId}
      onSubmit={() => onSubmit(buildGrantConsentOrder(factionId, vassalageId, action, targetId))}
      onCancel={onCancel}
    >
      <FormField label="Who">
        <select className={FORM_INPUT_CLASS} value={targetId} onChange={(event) => setTargetId(event.target.value)}>
          {targets.map((target) => (
            <option key={target.id} value={target.id}>{target.label}</option>
          ))}
        </select>
      </FormField>
      <FormField label="What your vassal may do">
        <select className={FORM_INPUT_CLASS} value={action} onChange={(event) => setAction(event.target.value as ConsentActionKind)}>
          {Object.entries(ACTION_LABELS).map(([value, label]) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>
      </FormField>
    </StrategyFormDialog>
  );
}
