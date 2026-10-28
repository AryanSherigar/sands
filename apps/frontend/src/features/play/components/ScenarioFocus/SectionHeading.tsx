import React from "react";

export interface SectionHeadingProps {
  label: string;
  id?: string;
  trailing?: React.ReactNode;
}

export const SectionHeading: React.FC<SectionHeadingProps> = ({
  label,
  id,
  trailing,
}) => {
  return (
    <div className="mb-4 flex items-center justify-between border-b border-border-subtle pb-3">
      <h2
        id={id}
        className="font-mono text-xs font-semibold uppercase tracking-[0.2em] text-content-faint"
      >
        {label}
      </h2>
      {trailing}
    </div>
  );
};
