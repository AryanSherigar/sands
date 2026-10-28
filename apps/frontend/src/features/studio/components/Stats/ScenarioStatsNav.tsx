import React from "react";
import type { ScenarioStatsNavProps } from "./ScenarioStatsNav.types";

export const ScenarioStatsNav: React.FC<ScenarioStatsNavProps> = ({ sections }) => (
  <nav aria-label="Stats sections" className="hidden lg:block">
    <ul className="sticky top-24 flex flex-col gap-2 font-sans text-sm">
      {sections.map((section) => (
        <li key={section.id}>
          <a
            href={`#${section.id}`}
            className="text-content-muted transition-colors hover:text-content"
          >
            {section.label}
          </a>
        </li>
      ))}
    </ul>
  </nav>
);
