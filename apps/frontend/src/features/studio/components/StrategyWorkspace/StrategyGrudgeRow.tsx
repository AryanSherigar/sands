import React from "react";
import { Button } from "@/shared/components/ui/Button";
import { Input } from "@/shared/components/ui/Input";
import { MAX_GRUDGE_REASON_CHARS, MAX_OPINION, MIN_OPINION } from "../../constants/strategyAuthoring";
import { removeGrudge, updateGrudge } from "../../lib/strategyStart";
import type { StrategyGrudgeRowProps } from "./StrategyWorkspace.types";

export const StrategyGrudgeRow: React.FC<StrategyGrudgeRowProps> = ({ grudge, holderName, targetName, onEdit }) => {
  const pair = `${holderName} toward ${targetName}`;
  return (
    <li className="space-y-2 rounded-sm border border-border-subtle p-3 text-sm">
      <div className="flex items-center justify-between">
        <span>{pair}</span>
        <Button
          variant="ghost"
          size="sm"
          aria-label={`Remove grudge, ${pair}`}
          onClick={() => onEdit((current) => removeGrudge(current, grudge.holder_id, grudge.target_id))}
        >
          Remove
        </Button>
      </div>
      <input
        type="range"
        aria-label={`Opinion, ${pair}`}
        min={MIN_OPINION}
        max={MAX_OPINION}
        value={grudge.opinion}
        onChange={(event) => {
          const opinion = Number(event.target.value);
          onEdit((current) => updateGrudge(current, grudge.holder_id, grudge.target_id, { opinion }));
        }}
      />
      <Input
        aria-label={`Reason, ${pair}`}
        maxLength={MAX_GRUDGE_REASON_CHARS}
        value={grudge.reason}
        onChange={(event) => {
          const reason = event.target.value;
          onEdit((current) => updateGrudge(current, grudge.holder_id, grudge.target_id, { reason }));
        }}
      />
    </li>
  );
};
