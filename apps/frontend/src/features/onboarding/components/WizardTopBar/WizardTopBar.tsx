import React from "react";
import type { WizardTopBarProps } from "./WizardTopBar.types";

export const WizardTopBar: React.FC<WizardTopBarProps> = ({ onSetUpLater }) => (
  <header className="flex w-full items-center justify-between py-5">
    <div className="flex items-center gap-2">
      <div className="flex items-center gap-2 font-display text-xl font-semibold tracking-tight text-content">
        <span
          className="inline-block h-2.5 w-2.5 rounded-full bg-content"
          aria-hidden="true"
        />
        <span>sands</span>
      </div>
      <span className="ml-1 rounded border border-border-subtle px-1.5 py-0.5 font-mono text-[11px] text-content-faint">
        Setup
      </span>
    </div>
    <button
      type="button"
      onClick={onSetUpLater}
      className="rounded-md px-2.5 py-1.5 text-xs font-medium text-content-muted transition-colors hover:bg-white/6 hover:text-content focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent"
    >
      Set up later
    </button>
  </header>
);
