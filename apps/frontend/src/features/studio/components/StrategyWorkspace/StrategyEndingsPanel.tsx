import React from "react";
import { Button } from "@/shared/components/ui/Button";
import { Input } from "@/shared/components/ui/Input";
import { Select, type SelectOption } from "@/shared/components/ui/Select";
import { ENDING_METRIC_OPTIONS } from "../../constants/strategyAuthoring";
import { makeUniqueId } from "../../lib/strategyIds";
import type {
  StrategyEnding,
  StrategyEndingToggles,
  StrategyFields,
} from "../../types/strategyDocument.types";

export interface StrategyEndingsPanelProps {
  fields: StrategyFields;
  onEdit: (change: (current: StrategyFields) => StrategyFields) => void;
}

const ENDING_KINDS: SelectOption[] = [
  { value: "victory", label: "Victory" },
  { value: "defeat", label: "Defeat" },
  { value: "graded", label: "Graded" },
];

const OPERATOR_OPTIONS: SelectOption[] = [
  { value: "gte", label: "At least (≥)" },
  { value: "lte", label: "At most (≤)" },
  { value: "eq", label: "Exactly (=)" },
];

const DEFAULT_ENDING_OPTIONS: readonly { key: keyof StrategyEndingToggles; label: string; desc: string }[] = [
  { key: "is_hegemony_enabled", label: "Hegemony victory", desc: "Win by holding 60% regions and wealth" },
  { key: "is_regime_fall_enabled", label: "Regime fall defeat", desc: "Lose from sustained collapse and low will" },
  { key: "is_negotiated_end_enabled", label: "Negotiated truce ending", desc: "Truce can conclude the campaign" },
  { key: "is_end_date_enabled", label: "End date score resolution", desc: "Grade outcome when timeline ends" },
  { key: "is_vassal_outcome_enabled", label: "Vassal submission outcome", desc: "Conclude campaign if player is vassal" },
];

function buildNewEnding(takenIds: readonly string[]): StrategyEnding {
  const name = `Objective ${takenIds.length + 1}`;
  return {
    id: makeUniqueId(name, takenIds),
    kind: "victory",
    name,
    condition: {
      kind: "comparison",
      metric: "region_count",
      subject_id: null,
      operator: "gte",
      value: 4,
    },
    epilogue_hint: "",
  };
}

const EndingToggleRow: React.FC<{
  option: (typeof DEFAULT_ENDING_OPTIONS)[number];
  isChecked: boolean;
  onToggle: (checked: boolean) => void;
}> = ({ option, isChecked, onToggle }) => (
  <label className="flex items-start gap-2 text-sm">
    <input
      type="checkbox"
      checked={isChecked}
      onChange={(event) => onToggle(event.target.checked)}
      className="mt-0.5"
    />
    <div>
      <span className="font-medium text-content">{option.label}</span>
      <p className="text-xs text-content-muted">{option.desc}</p>
    </div>
  </label>
);

const EndingItemCard: React.FC<{
  ending: StrategyEnding;
  index: number;
  onUpdate: (patch: Partial<StrategyEnding>) => void;
  onRemove: () => void;
}> = ({ ending, index, onUpdate, onRemove }) => {
  const metricOptions = ENDING_METRIC_OPTIONS.map((item) => ({ value: item.id, label: item.label }));

  return (
    <div className="space-y-3 rounded-md border border-border-subtle bg-surface-inset p-3">
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-semibold text-content-muted uppercase">Condition #{index + 1}</span>
        <Button variant="ghost" size="sm" onClick={onRemove}>
          Remove
        </Button>
      </div>
      <div className="grid gap-2 sm:grid-cols-2">
        <label className="block space-y-1 text-xs">
          Name
          <Input
            value={ending.name}
            onChange={(event) => onUpdate({ name: event.target.value })}
            placeholder="e.g. Conquer the Realm"
          />
        </label>
        <label className="block space-y-1 text-xs">
          Outcome Kind
          <Select
            value={ending.kind}
            options={ENDING_KINDS}
            onChange={(event) => onUpdate({ kind: event.target.value as StrategyEnding["kind"] })}
          />
        </label>
      </div>
      <div className="grid gap-2 sm:grid-cols-3">
        <label className="block space-y-1 text-xs">
          Target Metric
          <Select
            value={ending.condition.metric}
            options={metricOptions}
            onChange={(event) =>
              onUpdate({
                condition: { ...ending.condition, metric: event.target.value },
              })
            }
          />
        </label>
        <label className="block space-y-1 text-xs">
          Comparison
          <Select
            value={ending.condition.operator}
            options={OPERATOR_OPTIONS}
            onChange={(event) =>
              onUpdate({
                condition: { ...ending.condition, operator: event.target.value },
              })
            }
          />
        </label>
        <label className="block space-y-1 text-xs">
          Threshold Value
          <Input
            type="number"
            value={ending.condition.value}
            onChange={(event) =>
              onUpdate({
                condition: { ...ending.condition, value: Number(event.target.value) || 0 },
              })
            }
          />
        </label>
      </div>
      <label className="block space-y-1 text-xs">
        Epilogue Chronicler Hint (Optional)
        <Input
          value={ending.epilogue_hint ?? ""}
          onChange={(event) => onUpdate({ epilogue_hint: event.target.value })}
          placeholder="Guidance for the AI chronicler on what to emphasize..."
        />
      </label>
    </div>
  );
};

const MISSING_ENDING_HINT =
  "Without standard endings, publishing needs at least one victory and one defeat ending.";

function isMissingRequiredEnding(fields: StrategyFields): boolean {
  if (fields.is_using_default_endings) return false;
  const hasVictory = fields.endings.some((ending) => ending.kind === "victory");
  const hasDefeat = fields.endings.some((ending) => ending.kind === "defeat");
  return !hasVictory || !hasDefeat;
}

export const StrategyEndingsPanel: React.FC<StrategyEndingsPanelProps> = ({ fields, onEdit }) => {
  const handleToggleDefault = (isUsingDefault: boolean): void => {
    onEdit((current) => ({ ...current, is_using_default_endings: isUsingDefault }));
  };

  const handleEndingToggle = (key: keyof StrategyEndingToggles, isEnabled: boolean): void => {
    onEdit((current) => ({
      ...current,
      ending_toggles: { ...current.ending_toggles, [key]: isEnabled },
    }));
  };

  const handleAddEnding = (): void => {
    onEdit((current) => ({
      ...current,
      endings: [...current.endings, buildNewEnding(current.endings.map((item) => item.id))],
    }));
  };

  const handleUpdateEnding = (index: number, patch: Partial<StrategyEnding>): void => {
    onEdit((current) => ({
      ...current,
      endings: current.endings.map((item, i) => (i === index ? { ...item, ...patch } : item)),
    }));
  };

  const handleRemoveEnding = (index: number): void => {
    onEdit((current) => ({
      ...current,
      endings: current.endings.filter((_, i) => i !== index),
    }));
  };

  return (
    <div className="space-y-4">
      <div className="rounded border border-border-subtle bg-surface-inset p-3 space-y-3">
        <label className="flex items-center gap-2 text-sm font-medium">
          <input
            type="checkbox"
            checked={fields.is_using_default_endings}
            onChange={(event) => handleToggleDefault(event.target.checked)}
          />
          Use standard campaign endings
        </label>
        {fields.is_using_default_endings && (
          <div className="space-y-2 pl-6 pt-1 border-t border-border-subtle">
            {DEFAULT_ENDING_OPTIONS.map((option) => (
              <EndingToggleRow
                key={option.key}
                option={option}
                isChecked={fields.ending_toggles[option.key]}
                onToggle={(checked) => handleEndingToggle(option.key, checked)}
              />
            ))}
          </div>
        )}
      </div>

      {isMissingRequiredEnding(fields) && (
        <p role="alert" className="text-xs text-feedback-warning">
          {MISSING_ENDING_HINT}
        </p>
      )}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold">Authored Ending Objectives</h3>
            <p className="text-xs text-content-muted">Custom conditions that trigger victory or defeat upon being met.</p>
          </div>
          <Button type="button" variant="secondary" size="sm" onClick={handleAddEnding}>
            Add ending condition
          </Button>
        </div>
        {fields.endings.length === 0 ? (
          <p className="text-xs text-content-muted italic">No custom ending conditions defined yet.</p>
        ) : (
          <div className="space-y-2">
            {fields.endings.map((ending, index) => (
              <EndingItemCard
                key={ending.id}
                ending={ending}
                index={index}
                onUpdate={(patch) => handleUpdateEnding(index, patch)}
                onRemove={() => handleRemoveEnding(index)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
