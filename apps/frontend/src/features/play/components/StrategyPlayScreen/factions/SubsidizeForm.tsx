import { useState } from "react";
import { buildSubsidizeOrder } from "../../../lib/orderBuilders";
import type { FormOption } from "../../../lib/realmAffairs";
import type { StrategyOrder } from "../../../types/simulation.types";
import { FORM_INPUT_CLASS, FormField } from "../ui/FormField";
import { StrategyFormDialog } from "../ui/StrategyFormDialog";

export interface SubsidizeFormProps {
  factionId: string;
  warId: string;
  receivers: FormOption[];
  onSubmit: (order: StrategyOrder) => void;
  onCancel: () => void;
}

const DEFAULT_AMOUNT = 25;
const DEFAULT_TURNS = 4;

export function SubsidizeForm({ factionId, warId, receivers, onSubmit, onCancel }: SubsidizeFormProps) {
  const [receiverId, setReceiverId] = useState(receivers[0]?.id ?? "");
  const [amount, setAmount] = useState(DEFAULT_AMOUNT);
  const [turns, setTurns] = useState(DEFAULT_TURNS);
  const isValid = Boolean(receiverId) && amount >= 1 && turns >= 1;

  return (
    <StrategyFormDialog
      title="Subsidize a side"
      description="Pay gold each turn to help a realm keep fighting. It stops if you cannot pay."
      submitLabel="Pay the subsidy"
      isSubmitDisabled={!isValid}
      onSubmit={() => onSubmit(buildSubsidizeOrder(factionId, receiverId, warId, amount, turns))}
      onCancel={onCancel}
    >
      <FormField label="Who receives it">
        <select className={FORM_INPUT_CLASS} value={receiverId} onChange={(event) => setReceiverId(event.target.value)}>
          {receivers.map((receiver) => (
            <option key={receiver.id} value={receiver.id}>{receiver.label}</option>
          ))}
        </select>
      </FormField>
      <FormField label="Gold each turn">
        <input className={FORM_INPUT_CLASS} type="number" min={1} value={amount} onChange={(event) => setAmount(Number(event.target.value))} />
      </FormField>
      <FormField label="For how many turns">
        <input className={FORM_INPUT_CLASS} type="number" min={1} value={turns} onChange={(event) => setTurns(Number(event.target.value))} />
      </FormField>
    </StrategyFormDialog>
  );
}
