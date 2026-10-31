import React, { useState } from "react";
import { Input } from "@/shared/components/ui/Input";
import { clampWholeNumber } from "../../lib/strategyStart";
import type { StrategyNumberFieldProps } from "./StrategyWorkspace.types";

export const StrategyNumberField: React.FC<StrategyNumberFieldProps> = ({ label, value, max, onCommit }) => {
  const [draft, setDraft] = useState<string | null>(null);

  const handleCommit = (): void => {
    if (draft === null) return;
    onCommit(clampWholeNumber(draft, max));
    setDraft(null);
  };

  return (
    <label className="block space-y-1 text-sm">
      {label}
      <Input
        inputMode="numeric"
        value={draft ?? String(value)}
        onFocus={(event) => event.target.select()}
        onChange={(event) => setDraft(event.target.value)}
        onBlur={handleCommit}
        onKeyDown={(event) => event.key === "Enter" && handleCommit()}
      />
    </label>
  );
};
