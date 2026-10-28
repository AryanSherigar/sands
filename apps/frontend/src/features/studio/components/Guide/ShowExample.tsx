import React, { useState } from "react";
import { DEMO_STORY } from "../../constants/demoStory";
import type { ShowExampleProps } from "./Guide.types";

export const ShowExample: React.FC<ShowExampleProps> = ({ stepId }) => {
  const [isOpen, setIsOpen] = useState(false);
  const example = DEMO_STORY[stepId];
  if (!example) return null;

  const handleToggle = (): void => setIsOpen((current) => !current);

  return (
    <div className="space-y-2">
      <button
        type="button"
        aria-expanded={isOpen}
        onClick={handleToggle}
        className="text-meta font-medium text-content-muted underline underline-offset-4 transition-colors hover:text-content"
      >
        {isOpen ? "Hide the example" : "Show an example"}
      </button>
      {isOpen && (
        <aside
          aria-label="Example"
          className="space-y-2 rounded-md border border-border-subtle bg-surface-raised p-4 text-meta text-content-muted"
        >
          <p className="font-medium text-content">{example.heading}</p>
          {example.lines.map((line) => (
            <p key={line}>{line}</p>
          ))}
        </aside>
      )}
    </div>
  );
};
