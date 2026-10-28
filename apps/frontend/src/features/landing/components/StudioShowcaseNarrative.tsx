import React from "react";
import {
  IconTerminal2,
  IconFileText,
  IconBracketsContain,
} from "@tabler/icons-react";
import { ButtonLink } from "@/shared/components/ui/ButtonLink";
import {
  STUDIO_SHOWCASE_DESCRIPTION,
  STUDIO_SHOWCASE_LABEL,
  STUDIO_SHOWCASE_TITLE,
} from "../constants/landing.constants";

export const StudioShowcaseNarrative: React.FC = () => {
  return (
    <div className="flex flex-col items-start justify-center">
      <div className="mb-2 flex items-center gap-2">
        <span className="h-2 w-2 rounded-full bg-accent" />
        <span className="font-mono text-xs uppercase tracking-wider text-content-faint">
          {STUDIO_SHOWCASE_LABEL}
        </span>
      </div>
      <h2 className="font-display text-2xl font-semibold text-content md:text-3xl mb-3">
        {STUDIO_SHOWCASE_TITLE}
      </h2>
      <p className="font-sans text-sm leading-relaxed text-content-muted mb-6 max-w-xl">
        {STUDIO_SHOWCASE_DESCRIPTION}
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 w-full mb-6">
        <div className="rounded-md bg-surface-inset p-3.5 border border-border-subtle">
          <div className="flex items-center gap-2 font-display text-sm font-medium text-content mb-1">
            <IconFileText size={16} stroke={1.5} className="text-content-muted" />
            Simple Mode
          </div>
          <p className="font-sans text-xs text-content-faint leading-relaxed">
            Define premise, core lore, and tone. Perfect for rapid prose
            experiments and linear narratives.
          </p>
        </div>
        <div className="rounded-md bg-surface-inset p-3.5 border border-border-subtle">
          <div className="flex items-center gap-2 font-display text-sm font-medium text-content mb-1">
            <IconBracketsContain size={16} stroke={1.5} className="text-accent" />
            Advanced Mode
          </div>
          <p className="font-sans text-xs text-content-faint leading-relaxed">
            Structure custom entities, tracked values, strict transition rules,
            inventory, and canonical endings.
          </p>
        </div>
      </div>

      <ButtonLink
        to="/studio"
        variant="secondary"
        size="md"
      >
        <IconTerminal2 size={16} stroke={1.5} />
        Open Studio
      </ButtonLink>
    </div>
  );
};
