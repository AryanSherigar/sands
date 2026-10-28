import type React from "react";

export interface FilterRowProps {
  label: string;
  inputType: "checkbox" | "radio";
  name?: string;
  isChecked: boolean;
  leading?: React.ReactNode;
  onChange: () => void;
}
