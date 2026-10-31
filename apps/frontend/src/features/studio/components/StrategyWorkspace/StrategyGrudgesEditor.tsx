import React, { useState } from "react";
import { Button } from "@/shared/components/ui/Button";
import { Select } from "@/shared/components/ui/Select";
import { addGrudge } from "../../lib/strategyStart";
import { StrategyGrudgeRow } from "./StrategyGrudgeRow";
import type { StrategyGrudgesEditorProps } from "./StrategyWorkspace.types";

export const StrategyGrudgesEditor: React.FC<StrategyGrudgesEditorProps> = ({ fields, onEdit }) => {
  const [pickedHolder, setPickedHolder] = useState<string | null>(null);
  const [pickedTarget, setPickedTarget] = useState<string | null>(null);
  const holderId = pickedHolder ?? fields.leaders[0]?.id;
  const targetId = pickedTarget ?? fields.leaders[1]?.id;
  const options = fields.leaders.map((item) => ({ value: item.id, label: item.name }));
  const nameOf = (id: string): string => fields.leaders.find((item) => item.id === id)?.name ?? id;
  const canAdd = Boolean(holderId && targetId && holderId !== targetId);

  return (
    <section className="space-y-2">
      <h4 className="text-sm font-semibold">Grudges</h4>
      <div className="flex flex-wrap gap-2">
        <Select aria-label="Grudge holder" value={holderId ?? ""} options={options} onChange={(event) => setPickedHolder(event.target.value)} />
        <Select aria-label="Grudge target" value={targetId ?? ""} options={options} onChange={(event) => setPickedTarget(event.target.value)} />
        <Button
          variant="secondary"
          size="sm"
          disabled={!canAdd}
          onClick={() => holderId && targetId && onEdit((current) => addGrudge(current, holderId, targetId))}
        >
          Add grudge
        </Button>
      </div>
      <ul className="space-y-2">
        {fields.grudges.map((grudge) => (
          <StrategyGrudgeRow
            key={`${grudge.holder_id}-${grudge.target_id}`}
            grudge={grudge}
            holderName={nameOf(grudge.holder_id)}
            targetName={nameOf(grudge.target_id)}
            onEdit={onEdit}
          />
        ))}
      </ul>
    </section>
  );
};
