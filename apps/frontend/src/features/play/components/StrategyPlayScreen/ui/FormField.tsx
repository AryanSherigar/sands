import type { ReactNode } from "react";

export interface FormFieldProps {
  label: string;
  children: ReactNode;
}

export function FormField({ label, children }: FormFieldProps) {
  return (
    <label className="flex flex-col gap-1 text-[12px] font-semibold text-[#221a12]">
      {label}
      {children}
    </label>
  );
}

export const FORM_INPUT_CLASS =
  "rounded-md border border-[#3A3128]/20 bg-[#fff8f4] px-2 py-1.5 text-[13px] font-normal text-[#221a12]";
