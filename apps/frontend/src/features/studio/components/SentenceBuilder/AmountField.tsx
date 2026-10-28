import React from "react";
import { Input } from "@/shared/components/ui/Input";
import { Select } from "@/shared/components/ui/Select";
import { COMPARISON_PLACEHOLDER, NO_SELECTION } from "../../constants/sentenceBuilder";
import type { AmountFieldProps } from "./SentenceBuilder.types";

const parseAmount = (raw: string): number | undefined => {
  if (raw.trim() === "") return undefined;
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : undefined;
};

export const AmountField: React.FC<AmountFieldProps> = ({ row, option, numberOptions, onChange }) => {
  if (row.ref !== undefined) {
    const choices = numberOptions
      .filter((other) => other.path !== option.path)
      .map((other) => ({ value: other.path, label: other.label }));
    return (
      <Select
        aria-label="Other value"
        className="w-auto min-w-36"
        value={row.ref}
        options={[{ value: NO_SELECTION, label: COMPARISON_PLACEHOLDER }, ...choices]}
        onChange={(event) => onChange({ ...row, ref: event.target.value })}
      />
    );
  }
  if (option.kind === "number") {
    return (
      <div className="w-24">
        <Input
          type="number"
          aria-label="Amount"
          min={option.min}
          max={option.max}
          value={typeof row.amount === "number" ? row.amount : ""}
          onChange={(event) => onChange({ ...row, amount: parseAmount(event.target.value) })}
        />
      </div>
    );
  }
  if (option.kind !== "enum") return null;
  if (!option.options?.length) {
    return (
      <div className="w-32">
        <Input
          aria-label="Choice"
          value={typeof row.amount === "string" ? row.amount : ""}
          onChange={(event) => onChange({ ...row, amount: event.target.value })}
        />
      </div>
    );
  }
  return (
    <Select
      aria-label="Choice"
      className="w-auto min-w-32"
      value={typeof row.amount === "string" ? row.amount : ""}
      options={[
        { value: NO_SELECTION, label: COMPARISON_PLACEHOLDER },
        ...option.options.map((choice) => ({ value: choice, label: choice })),
      ]}
      onChange={(event) => onChange({ ...row, amount: event.target.value })}
    />
  );
};
