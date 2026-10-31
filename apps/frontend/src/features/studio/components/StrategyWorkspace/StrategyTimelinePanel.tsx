import React from "react";
import { Select } from "@/shared/components/ui/Select";
import { MONTHS_PER_YEAR } from "../../constants/strategyAuthoring";
import { countTurns, setTiming } from "../../lib/strategyStart";
import { StrategyNumberField } from "./StrategyNumberField";
import type { StrategyTimelinePanelProps } from "./StrategyWorkspace.types";

const MONTH_OPTIONS = Array.from({ length: MONTHS_PER_YEAR }, (_, index) => ({
  value: String(index + 1),
  label: new Date(2000, index, 1).toLocaleString("en", { month: "long" }),
}));

export const StrategyTimelinePanel: React.FC<StrategyTimelinePanelProps> = ({ fields, onEdit }) => {
  const { timing } = fields;
  return (
    <div className="space-y-3">
      <div className="grid gap-3 sm:grid-cols-3">
        <StrategyNumberField
          label="Start year"
          value={timing.start_year}
          onCommit={(start_year) => onEdit((current) => setTiming(current, { start_year }))}
        />
        <label className="block space-y-1 text-sm">
          Start month
          <Select
            value={String(timing.start_month)}
            options={MONTH_OPTIONS}
            onChange={(event) => {
              const startMonth = Number(event.target.value);
              onEdit((current) => setTiming(current, { start_month: startMonth }));
            }}
          />
        </label>
        <StrategyNumberField
          label="End year"
          value={timing.end_year}
          onCommit={(end_year) => onEdit((current) => setTiming(current, { end_year }))}
        />
      </div>
      <p className="text-sm text-content-muted">{`About ${countTurns(timing)} turns`}</p>
    </div>
  );
};
