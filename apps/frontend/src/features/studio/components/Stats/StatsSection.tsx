import React from "react";
import type { StatsSectionProps } from "./StatsSection.types";

export const StatsSection: React.FC<StatsSectionProps> = ({ section, children }) => (
  <section
    id={section.id}
    aria-labelledby={`${section.id}-heading`}
    className="flex scroll-mt-24 flex-col gap-4"
  >
    <h2
      id={`${section.id}-heading`}
      className="font-mono text-xs font-semibold uppercase tracking-widest text-content-muted"
    >
      {section.label}
    </h2>
    {children}
  </section>
);
