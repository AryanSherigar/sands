import React from "react";
import { useParams, useSearchParams, Link } from "react-router-dom";
import { IconAlertCircle } from "@tabler/icons-react";
import { useScenario } from "../hooks/useScenario";
import { useStudioStore } from "../stores/studio.store";
import { MasterModeStudioLayout } from "../components/Layout/MasterModeStudioLayout";

import { SaveStatusIndicator } from "../components/SaveStatusIndicator/SaveStatusIndicator";
import { STATS_VISIBLE_STATUSES } from "../constants/stats";
import { FULL_EDITOR_PARAM, FULL_EDITOR_VALUE } from "../constants/studioFrame";

export const EditScenarioPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const { scenario, isLoading, error } = useScenario(id ?? null);
  const isSaving = useStudioStore((s) => s.isSaving);
  const lastSaved = useStudioStore((s) => s.lastSaved);

  if (!id) {
    return (
      <div className="flex min-h-dvh h-dvh items-center justify-center bg-surface-sunken font-sans text-sm text-content-muted">
        No scenario ID provided.
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex min-h-dvh h-dvh items-center justify-center bg-surface-sunken font-sans text-sm text-content-muted">
        Loading scenario…
      </div>
    );
  }

  if (error || !scenario) {
    return (
      <div className="flex min-h-dvh h-dvh items-center justify-center gap-2 bg-surface-sunken font-sans text-sm text-danger">
        <IconAlertCircle size={18} stroke={1.5} aria-hidden="true" />
        Failed to load scenario.
      </div>
    );
  }

  const hasStats = STATS_VISIBLE_STATUSES.includes(scenario.status);
  const isFullEditorRequested = searchParams.get(FULL_EDITOR_PARAM) === FULL_EDITOR_VALUE;

  return (
    <div className="flex min-h-dvh h-dvh flex-col overflow-hidden bg-surface-sunken font-sans text-content">
      <header className="z-50 flex shrink-0 items-center justify-between gap-4 border-b border-border-subtle bg-surface-sunken px-5 py-2">
        <div className="flex min-w-0 items-center gap-5">
          <Link
            to="/"
            className="shrink-0 font-mono text-sm font-semibold lowercase tracking-[0.25em] text-content transition-colors hover:text-content-muted"
          >
            sands
          </Link>
          <nav className="hidden shrink-0 items-center gap-1 lg:flex">
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
          <h1 className="truncate font-mono text-sm font-semibold uppercase tracking-widest text-content-faint">
            {scenario.title || "Untitled scenario"}
          </h1>
        </div>
        <div className="flex items-center gap-4 font-mono text-xs uppercase tracking-wider">
          {isFullEditorRequested && (
            <Link
              to={`/studio/${id}/edit`}
              className="shrink-0 text-content-muted transition-colors hover:text-content"
            >
              Back to Guide
            </Link>
          )}
          {hasStats && (
            <Link
              to={`/studio/${id}/stats`}
              className="shrink-0 text-content-muted transition-colors hover:text-content"
            >
              Stats
            </Link>
          )}
          <SaveStatusIndicator isSaving={isSaving} lastSaved={lastSaved} />
          <span className="shrink-0 text-content-faint">Master mode</span>
        </div>
      </header>
      <main className="flex-1 flex flex-col relative min-h-0">
        <MasterModeStudioLayout scenarioId={id} />
      </main>
    </div>
  );
};
