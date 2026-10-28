import React from "react";
import { IconTrophy } from "@tabler/icons-react";
import type { WorldmakerRevealProps } from "./PublishSuccess.types";

export const WorldmakerReveal: React.FC<WorldmakerRevealProps> = ({ achievement }) => (
  <aside
    aria-label="Achievement unlocked"
    className="flex items-center gap-3 rounded-md border border-border-strong bg-surface-raised px-4 py-3"
  >
    <IconTrophy size={20} aria-hidden="true" className="text-accent" />
    <div>
      <p className="text-body font-medium text-content">Achievement unlocked: {achievement.name}</p>
      <p className="text-meta text-content-muted">{achievement.requirement}</p>
    </div>
  </aside>
);
