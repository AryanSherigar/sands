import { useState } from "react";
import { buildVassalDemandOrder } from "../../../lib/orderBuilders";
import type { StrategyOrder, VassalDemandKind } from "../../../types/simulation.types";
import { FORM_INPUT_CLASS, FormField } from "../ui/FormField";
import { StrategyFormDialog } from "../ui/StrategyFormDialog";

export interface VassalDemandFormProps {
  factionId: string;
  vassalageId: string;
  tributePercent: number;
  levyPercent: number;
  onSubmit: (order: StrategyOrder) => void;
  onCancel: () => void;
}

const DEMAND_LABELS: Record<VassalDemandKind, string> = {
  tribute: "More tribute (share of income, %)",
  levy: "More levy (share of manpower, %)",
  garrison: "A garrison in their lands (troops)",
};
const DEFAULT_EXCESS = 10;
const DEFAULT_GARRISON = 100;

function treatyShareFor(kind: VassalDemandKind, tributePercent: number, levyPercent: number): number {
  if (kind === "tribute") return tributePercent;
  if (kind === "levy") return levyPercent;
  return 0;
}

function defaultAmountFor(kind: VassalDemandKind, tributePercent: number, levyPercent: number): number {
  return kind === "garrison" ? DEFAULT_GARRISON : treatyShareFor(kind, tributePercent, levyPercent) + DEFAULT_EXCESS;
}

export function VassalDemandForm({
  factionId,
  vassalageId,
  tributePercent,
  levyPercent,
  onSubmit,
  onCancel,
}: VassalDemandFormProps) {
  const [kind, setKind] = useState<VassalDemandKind>("tribute");
  const [amount, setAmount] = useState(tributePercent + DEFAULT_EXCESS);
  const treatyShare = treatyShareFor(kind, tributePercent, levyPercent);
  const isExcess = kind === "garrison" ? amount >= 1 : amount > treatyShare;

  return (
    <StrategyFormDialog
      title="Make a demand of your vassal"
      description="A demand beyond the treaty angers the regions it touches at once. Your vassal may accept, bargain, refuse or rebel."
      submitLabel="Send the demand"
      isSubmitDisabled={!isExcess}
      onSubmit={() => onSubmit(buildVassalDemandOrder(factionId, vassalageId, kind, amount))}
      onCancel={onCancel}
    >
      <FormField label="Demand">
        <select
          className={FORM_INPUT_CLASS}
          value={kind}
          onChange={(event) => {
            const next = event.target.value as VassalDemandKind;
            setKind(next);
            setAmount(defaultAmountFor(next, tributePercent, levyPercent));
          }}
        >
          {(Object.keys(DEMAND_LABELS) as VassalDemandKind[]).map((option) => (
            <option key={option} value={option}>{DEMAND_LABELS[option]}</option>
          ))}
        </select>
      </FormField>
      <FormField label={kind === "garrison" ? "Troops" : `Amount (the treaty gives you ${treatyShare}%)`}>
        <input className={FORM_INPUT_CLASS} type="number" min={1} value={amount} onChange={(event) => setAmount(Number(event.target.value))} />
      </FormField>
    </StrategyFormDialog>
  );
}
