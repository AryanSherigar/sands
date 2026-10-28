import React, { useEffect, useRef, useState } from "react";
import { Input } from "@/shared/components/ui/Input";
import type { NumberFieldProps } from "./Advanced.types";

const toText = (value: number | undefined): string => (value === undefined ? "" : String(value));

const parseNumber = (text: string): number | undefined | null => {
  if (text.trim() === "") return undefined;
  const parsed = Number(text);
  return Number.isFinite(parsed) ? parsed : null;
};

export const NumberField: React.FC<NumberFieldProps> = ({ label, value, placeholder, onChange, onBlur }) => {
  const [text, setText] = useState(toText(value));
  const lastValue = useRef(value);

  useEffect(() => {
    if (value === lastValue.current) return;
    lastValue.current = value;
    setText(toText(value));
  }, [value]);

  const handleChange = (event: React.ChangeEvent<HTMLInputElement>): void => {
    setText(event.target.value);
    const parsed = parseNumber(event.target.value);
    if (parsed === null) return;
    lastValue.current = parsed;
    onChange(parsed);
  };

  return (
    <label className="block space-y-1 text-meta text-content-muted">
      {label}
      <Input type="text" inputMode="decimal" value={text} placeholder={placeholder} onChange={handleChange} onBlur={onBlur} />
    </label>
  );
};
