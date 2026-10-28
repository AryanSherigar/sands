import React from "react";
import { Input } from "@/shared/components/ui/Input";
import { Select } from "@/shared/components/ui/Select";
import { NO_SELECTION } from "../../../constants/sentenceBuilder";
import type { ChangeRow } from "../../../lib/changeRows";
import type { ChangeAmountInputProps } from "./Advanced.types";

const YES_NO_OPTIONS = [
  { value: "yes", label: "Yes" },
  { value: "no", label: "No" },
];

const readYesNo = (value: ChangeRow["value"]): string => {
  if (value === undefined) return NO_SELECTION;
  return value ? "yes" : "no";
};

export const ChangeAmountInput: React.FC<ChangeAmountInputProps> = ({ row, option, onChange }) => {
  if (option.kind === "number") {
    return (
      <div className="w-24">
        <Input
          type="number"
          aria-label="Amount"
          value={typeof row.value === "number" && !Number.isNaN(row.value) ? row.value : ""}
          onChange={(event) => onChange(event.target.value === "" ? undefined : Number(event.target.value))}
        />
      </div>
    );
  }
  if (option.kind === "boolean") {
    return (
      <Select
        aria-label="Amount"
        className="w-auto min-w-24"
        value={readYesNo(row.value)}
        options={[{ value: NO_SELECTION, label: "Choose…" }, ...YES_NO_OPTIONS]}
        onChange={(event) => onChange(event.target.value === "" ? undefined : event.target.value === "yes")}
      />
    );
  }
  const choices = option.options ?? [];
  if (choices.length === 0) {
    return (
      <div className="w-32">
        <Input
          aria-label="Amount"
          value={typeof row.value === "string" ? row.value : ""}
          onChange={(event) => onChange(event.target.value || undefined)}
        />
      </div>
    );
  }
  return (
    <Select
      aria-label="Amount"
      className="w-auto min-w-32"
      value={typeof row.value === "string" ? row.value : NO_SELECTION}
      options={[
        { value: NO_SELECTION, label: "Choose…" },
        ...choices.map((choice) => ({ value: choice, label: choice })),
      ]}
      onChange={(event) => onChange(event.target.value || undefined)}
    />
  );
};
