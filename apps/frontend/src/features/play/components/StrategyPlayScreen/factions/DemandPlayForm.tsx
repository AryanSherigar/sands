import { useState } from "react";
import { buildDemandPlayOrder } from "../../../lib/orderBuilders";
import type { FormOption } from "../../../lib/realmAffairs";
import type { DemandTerm, StrategyOrder } from "../../../types/simulation.types";
import { FORM_INPUT_CLASS, FormField } from "../ui/FormField";
import { StrategyFormDialog } from "../ui/StrategyFormDialog";

export interface DemandPlayFormProps {
  factionId: string;
  targetFactionId: string;
  targetName: string;
  targetRegions: FormOption[];
  onSubmit: (order: StrategyOrder) => void;
  onCancel: () => void;
}

function buildTerms(
  factionId: string,
  targetFactionId: string,
  regionIds: string[],
  gold: number,
): DemandTerm[] {
  const regionTerms: DemandTerm[] = regionIds.map((regionId) => ({
    kind: "cede_region",
    from_faction_id: targetFactionId,
    to_faction_id: factionId,
    region_id: regionId,
  }));
  const goldTerms: DemandTerm[] =
    gold > 0 ? [{ kind: "pay_gold", payer_id: targetFactionId, payee_id: factionId, amount: gold }] : [];
  return [...regionTerms, ...goldTerms];
}

export function DemandPlayForm({
  factionId,
  targetFactionId,
  targetName,
  targetRegions,
  onSubmit,
  onCancel,
}: DemandPlayFormProps) {
  const [regionIds, setRegionIds] = useState<string[]>([]);
  const [gold, setGold] = useState(0);
  const terms = buildTerms(factionId, targetFactionId, regionIds, gold);

  const toggleRegion = (regionId: string): void => {
    setRegionIds((current) =>
      current.includes(regionId) ? current.filter((id) => id !== regionId) : [...current, regionId],
    );
  };

  return (
    <StrategyFormDialog
      title={`Make demands of ${targetName}`}
      description="They answer at the start of next turn. If they refuse, this opens a war."
      submitLabel="Send the demand"
      isSubmitDisabled={terms.length === 0}
      onSubmit={() => onSubmit(buildDemandPlayOrder(factionId, targetFactionId, terms))}
      onCancel={onCancel}
    >
      <fieldset className="flex flex-col gap-1">
        <legend className="mb-1 text-[12px] font-semibold text-[#221a12]">Regions to cede</legend>
        {targetRegions.length === 0 ? (
          <p className="text-[12px] italic text-[#72787c]">No regions of theirs are in sight.</p>
        ) : (
          targetRegions.map((region) => (
            <label key={region.id} className="flex items-center gap-2 text-[13px] text-[#221a12]">
              <input type="checkbox" checked={regionIds.includes(region.id)} onChange={() => toggleRegion(region.id)} />
              {region.label}
            </label>
          ))
        )}
      </fieldset>
      <FormField label="Gold to pay">
        <input className={FORM_INPUT_CLASS} type="number" min={0} value={gold} onChange={(event) => setGold(Number(event.target.value))} />
      </FormField>
    </StrategyFormDialog>
  );
}
