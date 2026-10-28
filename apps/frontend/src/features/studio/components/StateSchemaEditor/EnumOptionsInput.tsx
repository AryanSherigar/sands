import React, { useState } from "react";
import { Input } from "@/shared/components/ui/Input";
import { EnumOptionsInputProps } from "./EnumOptionsInput.types";

const parseOptions = (text: string): string[] =>
  text
    .split(",")
    .map((item) => item.trim())
    .filter((item) => item !== "");

export const EnumOptionsInput: React.FC<EnumOptionsInputProps> = ({
  options,
  onChange,
}) => {
  const hasLabelledOptions = (options ?? []).some(
    (option) => typeof option !== "string",
  );
  const [draft, setDraft] = useState(
    (options ?? []).map((option) => (typeof option === "string" ? option : option.value)).join(", "),
  );
  if (hasLabelledOptions) {
    return (
      <p className="text-xs text-content-faint">
        This field has options with labels; edit them in the scenario data.
      </p>
    );
  }

  const handleChange = (event: React.ChangeEvent<HTMLInputElement>): void => {
    setDraft(event.target.value);
    onChange(parseOptions(event.target.value));
  };

  return (
    <Input
      aria-label="Field options"
      value={draft}
      onChange={handleChange}
      placeholder="options, comma separated"
    />
  );
};
