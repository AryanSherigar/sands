import React, { useState } from "react";
import { Button } from "@/shared/components/ui/Button";
import { Input } from "@/shared/components/ui/Input";
import { Select } from "@/shared/components/ui/Select";
import { RULE_HANDS, RuleHand } from "@/shared/types/rule-sheet.types";
import {
  HAND_LABELS,
  INITIAL_STATUSES,
  InitialRuleStatus,
  MAX_RULE_NUMBER,
  MAX_RULE_TEXT_LENGTH,
  RULE_KEY_PATTERN,
  STATUS_LABELS,
} from "../../constants/sheetRule";
import { SheetRuleFormProps } from "./SheetRuleForm.types";

const HAND_OPTIONS = RULE_HANDS.map((hand) => ({
  value: hand,
  label: HAND_LABELS[hand],
}));
const STATUS_OPTIONS = INITIAL_STATUSES.map((status) => ({
  value: status,
  label: STATUS_LABELS[status],
}));

const suggestKey = (number: number): string => `r${number}`;

export const SheetRuleForm: React.FC<SheetRuleFormProps> = ({
  rule,
  existingKeys,
  nextNumber,
  onSubmit,
  onCancel,
  isSubmitting,
  submitError,
}) => {
  const [key, setKey] = useState(rule?.key ?? suggestKey(nextNumber));
  const [number, setNumber] = useState(rule?.number ?? nextNumber);
  const [text, setText] = useState(rule?.text ?? "");
  const [corruptedText, setCorruptedText] = useState(rule?.corrupted_text ?? "");
  const [status, setStatus] = useState<InitialRuleStatus>(
    rule?.initial_status ?? "intact",
  );
  const [hand, setHand] = useState<RuleHand>(rule?.source_style ?? "typed");
  const [isFlaggable, setIsFlaggable] = useState(rule?.is_ai_flaggable ?? false);

  const isKeyTaken = !rule && existingKeys.includes(key);
  const problems = [
    ...(RULE_KEY_PATTERN.test(key) ? [] : ["The key uses lowercase letters, digits and underscores."]),
    ...(isKeyTaken ? ["That key is already used by another rule."] : []),
    ...(text.trim() ? [] : ["The rule needs text."]),
  ];

  const handleSubmit = (event: React.FormEvent): void => {
    event.preventDefault();
    if (problems.length > 0) return;
    onSubmit({
      key,
      number,
      text,
      corrupted_text: corruptedText.trim() ? corruptedText : null,
      initial_status: status,
      source_style: hand,
      is_ai_flaggable: isFlaggable,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div className="grid grid-cols-2 gap-2">
        <Input
          aria-label="Key"
          value={key}
          disabled={Boolean(rule)}
          onChange={(event) => setKey(event.target.value)}
        />
        <Input
          aria-label="Number"
          type="number"
          min={1}
          max={MAX_RULE_NUMBER}
          value={number}
          onChange={(event) => setNumber(Number(event.target.value))}
        />
      </div>
      <textarea
        aria-label="Rule text"
        value={text}
        maxLength={MAX_RULE_TEXT_LENGTH}
        onChange={(event) => setText(event.target.value)}
        className="rounded-md w-full border border-border-subtle bg-surface px-3 py-2 text-sm text-content-muted"
        rows={3}
      />
      <textarea
        aria-label="Corrupted text"
        value={corruptedText}
        maxLength={MAX_RULE_TEXT_LENGTH}
        onChange={(event) => setCorruptedText(event.target.value)}
        placeholder="Optional. Leave blank to glitch the original when corrupted."
        className="rounded-md w-full border border-border-subtle bg-surface px-3 py-2 text-sm text-content-muted"
        rows={2}
      />
      <div className="grid grid-cols-2 gap-2">
        <Select
          aria-label="Starts as"
          options={STATUS_OPTIONS}
          value={status}
          onChange={(event) => setStatus(event.target.value as InitialRuleStatus)}
        />
        <Select
          aria-label="Written in"
          options={HAND_OPTIONS}
          value={hand}
          onChange={(event) => setHand(event.target.value as RuleHand)}
        />
      </div>
      <label className="flex items-center gap-2 text-sm text-content-muted">
        <input
          type="checkbox"
          checked={isFlaggable}
          onChange={(event) => setIsFlaggable(event.target.checked)}
        />
        The narrator may report breaking this rule
      </label>
      <p className="text-xs text-content-faint">
        Use this for rules the game cannot check from tracked values, such as
        &quot;do not look at the glass&quot;. Other rules change status through
        active rules that set rule_status.{key || "key"}.
      </p>
      {problems.length > 0 && (
        <ul role="alert" className="list-disc pl-5 text-xs text-warning">
          {problems.map((problem) => (
            <li key={problem}>{problem}</li>
          ))}
        </ul>
      )}
      {submitError && (
        <p role="alert" className="text-xs text-danger">
          {submitError}
        </p>
      )}
      <div className="flex justify-end gap-2">
        <Button type="button" variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" disabled={problems.length > 0 || isSubmitting}>
          {isSubmitting ? "Saving…" : "Save"}
        </Button>
      </div>
    </form>
  );
};
