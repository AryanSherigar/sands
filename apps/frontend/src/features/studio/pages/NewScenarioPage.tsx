import React, { useEffect } from "react";
import { Link } from "react-router-dom";
import { useStudioStore } from "../stores/studio.store";
import { MasterModeCreateFlow } from "../components/MasterModeCreateFlow/MasterModeCreateFlow";
import { SaveStatusIndicator } from "../components/SaveStatusIndicator/SaveStatusIndicator";

export const NewScenarioPage: React.FC = () => {
  const { isSaving, lastSaved, resetSaveState } = useStudioStore();

  useEffect(() => {
    resetSaveState();
  }, [resetSaveState]);

  return (
    <div className="flex min-h-[100dvh] h-dvh flex-col overflow-hidden bg-surface-sunken font-sans text-content">
      {/* Legacy master-mode creation: nav + save status */}
      <header className="z-50 flex shrink-0 items-center justify-between gap-4 border-b border-border-subtle bg-surface-sunken px-5 py-2">
        <div className="flex items-center gap-5">
          <Link
            to="/"
            className="font-mono text-sm font-semibold lowercase tracking-[0.25em] text-content transition-colors hover:text-content-muted"
          >
            sands
          </Link>
          <nav className="hidden items-center gap-1 lg:flex">
            <Link
              to="/"
              className="rounded-md px-2.5 py-1.5 font-sans text-sm text-content-muted transition-colors hover:text-content"
            >
              Home
            </Link>
            <Link
              to="/discover"
              className="rounded-md px-2.5 py-1.5 font-sans text-sm text-content-muted transition-colors hover:text-content"
            >
              Discover
            </Link>
            <Link
              to="/studio"
              className="rounded-md px-2.5 py-1.5 font-sans text-sm text-content transition-colors hover:text-content"
            >
              Studio
            </Link>
          </nav>
        </div>

        {/* Status indicator */}
        <div className="flex items-center gap-2 font-mono text-xs uppercase tracking-wider">
          <SaveStatusIndicator isSaving={isSaving} lastSaved={lastSaved} />
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col relative min-h-0">
        <MasterModeCreateFlow />
      </main>
    </div>
  );
};
