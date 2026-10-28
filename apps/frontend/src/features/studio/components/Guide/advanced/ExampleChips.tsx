import React from "react";
import type { ExampleChipsProps } from "./Advanced.types";

export const ExampleChips: React.FC<ExampleChipsProps> = ({ heading, examples, onPick }) => (
  <section aria-label={heading} className="space-y-2">
    <p className="text-meta font-medium text-content-muted">{heading}</p>
    <ul className="flex flex-wrap gap-2">
      {examples.map((example) => (
        <li key={example.id}>
          <button
            type="button"
            onClick={() => onPick(example.id)}
            className="rounded-sm border border-border-strong bg-surface-inset px-3 py-1.5 text-left text-meta text-content-muted transition-colors hover:text-content focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-primary"
          >
            {example.label}
          </button>
        </li>
      ))}
    </ul>
  </section>
);
