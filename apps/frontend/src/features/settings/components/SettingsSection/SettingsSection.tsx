import React from "react";
import type { SettingsSectionProps } from "./SettingsSection.types";

export const SettingsSection: React.FC<SettingsSectionProps> = ({
  id,
  title,
  children,
}) => (
  <section aria-labelledby={`${id}-heading`} id={id} className="space-y-4">
    <h2
      id={`${id}-heading`}
      className="border-b border-border-subtle pb-3 font-mono text-xs font-semibold uppercase tracking-[0.2em] text-content-faint"
    >
      {title}
    </h2>
    {children}
  </section>
);
