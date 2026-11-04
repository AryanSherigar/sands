import { useState } from "react";
import type { TroopType } from "../../../types/simulation.types";
import { FORM_INPUT_CLASS, FormField } from "../ui/FormField";
import { StrategyFormDialog } from "../ui/StrategyFormDialog";

export interface SplitArmyFormProps {
  troops: Partial<Record<TroopType, number>>;
  onSubmit: (troops: Partial<Record<TroopType, number>>) => void;
  onCancel: () => void;
}

const formatTroopLabel = (troopType: string): string => troopType.replace(/_/g, " ");

function toDetachment(
  troops: Partial<Record<TroopType, number>>,
  counts: Record<string, number>,
): Partial<Record<TroopType, number>> {
  const detachment: Partial<Record<TroopType, number>> = {};
  for (const [troopType, available] of Object.entries(troops)) {
    const taken = Math.min(counts[troopType] ?? 0, available);
    if (taken > 0) detachment[troopType as TroopType] = taken;
  }
  return detachment;
}

export function SplitArmyForm({ troops, onSubmit, onCancel }: SplitArmyFormProps) {
  const [counts, setCounts] = useState<Record<string, number>>({});
  const detachment = toDetachment(troops, counts);
  const takenTotal = Object.values(detachment).reduce((sum, count) => sum + count, 0);
  const availableTotal = Object.values(troops).reduce((sum, count) => sum + count, 0);
  const isValid = takenTotal > 0 && takenTotal < availableTotal;

  return (
    <StrategyFormDialog
      title="Split the army"
      description="Draw a detachment into its own army. It starts in the same place and can be ordered separately."
      submitLabel="Split off"
      isSubmitDisabled={!isValid}
      onSubmit={() => onSubmit(detachment)}
      onCancel={onCancel}
    >
      {Object.entries(troops).map(([troopType, available]) => (
        <FormField key={troopType} label={`${formatTroopLabel(troopType)} (of ${available.toLocaleString()})`}>
          <input
            className={FORM_INPUT_CLASS}
            type="number"
            min={0}
            max={available}
            value={counts[troopType] ?? 0}
            onChange={(event) =>
              setCounts({ ...counts, [troopType]: Math.min(Math.max(Number(event.target.value) || 0, 0), available) })
            }
          />
        </FormField>
      ))}
      {isValid ? null : (
        <p className="text-[12px] text-[#72787c]">Take some troops, but leave some behind.</p>
      )}
    </StrategyFormDialog>
  );
}
