import React from "react";

interface SetupStageHeaderProps {
  title?: string;
}

export const SetupStageHeader: React.FC<SetupStageHeaderProps> = ({
  title,
}) => (
  <div className="text-center space-y-3 pb-6 border-b border-border-subtle">
    <div className="flex items-center justify-center gap-2">
      <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-content-muted bg-surface-inset px-2.5 py-0.5 rounded-sm border border-border-subtle">
        CAMPAIGN INITIATION
      </span>
    </div>

    <h1 className="font-display text-2xl sm:text-3xl font-bold text-content tracking-tight">
      {title || "Scenario Setup"}
    </h1>

    <p className="font-mono text-xs text-content-muted max-w-md mx-auto">
      Craft your starting parameters before the AI Narrator weaves your fate.
    </p>
  </div>
);
