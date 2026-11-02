import { useState } from "react";
import type { GroundKind, GroundView } from "../../../types/simulation.types";
import { FORM_INPUT_CLASS, FormField } from "../ui/FormField";
import { StrategyFormDialog } from "../ui/StrategyFormDialog";

export interface DeclareWarFormProps {
  targetName: string;
  grounds: GroundView[];
  regionNames?: Record<string, string>;
  onSubmit: (groundId: string | null) => void;
  onCancel: () => void;
}

const NO_GROUND = "";

const GROUND_LABELS: Record<GroundKind, string> = {
  claim: "A claim",
  broken_promise: "A broken promise",
  insult: "An insult",
  holy_war: "A holy war",
  refused_demand: "A refused demand",
  independence: "A war of independence",
};

function describeGround(ground: GroundView, regionNames: Record<string, string>): string {
  const base = GROUND_LABELS[ground.kind] ?? ground.kind;
  const region = ground.region_id ? regionNames[ground.region_id] ?? ground.region_id : null;
  return region ? `${base}: ${region}` : base;
}

export function DeclareWarForm({ targetName, grounds, regionNames = {}, onSubmit, onCancel }: DeclareWarFormProps) {
  const [groundId, setGroundId] = useState(grounds[0]?.id ?? NO_GROUND);

  return (
    <StrategyFormDialog
      title={`Declare war on ${targetName}`}
      description="A just cause makes the war easier to defend. Without one, declaring war costs reputation and stability."
      submitLabel="Declare war"
      onSubmit={() => onSubmit(groundId === NO_GROUND ? null : groundId)}
      onCancel={onCancel}
    >
      <FormField label="Your cause">
        <select className={FORM_INPUT_CLASS} value={groundId} onChange={(event) => setGroundId(event.target.value)}>
          {grounds.map((ground) => (
            <option key={ground.id} value={ground.id}>{describeGround(ground, regionNames)}</option>
          ))}
          <option value={NO_GROUND}>No cause</option>
        </select>
      </FormField>
    </StrategyFormDialog>
  );
}
