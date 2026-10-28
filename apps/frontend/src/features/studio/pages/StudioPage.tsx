import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/shared/components/ui/Button";
import { useDebouncedValue } from "@/shared/hooks/useDebouncedValue";
import { useLoadMoreTrigger } from "@/shared/hooks/useLoadMoreTrigger";
import { useToast } from "@/shared/hooks/useToast";
import { DeleteScenarioDialog } from "../components/StudioList/DeleteScenarioDialog";
import { ScenarioRowSkeletonList } from "../components/StudioList/ScenarioRowSkeletonList";
import { StudioEmptyState } from "../components/StudioList/StudioEmptyState";
import { StudioFilterBar } from "../components/StudioList/StudioFilterBar";
import { StudioScenarioRow } from "../components/StudioList/StudioScenarioRow";
import {
  FIRST_LOAD_SKELETON_COUNT,
  NEXT_PAGE_SKELETON_COUNT,
  STUDIO_SEARCH_DEBOUNCE_MS,
  UNTITLED_SCENARIO_TITLE,
} from "../constants/studio-list";
import { useCreateStrategyScenario } from "../hooks/useCreateStrategyScenario";
import { useDeleteScenario } from "../hooks/useDeleteScenario";
import { useMyScenarios } from "../hooks/useMyScenarios";
import type { MyScenarioSummary, StudioTab } from "../types/scenario.types";

export const StudioPage: React.FC = () => {
  const navigate = useNavigate();
  const showToast = useToast();
  const { deleteScenario } = useDeleteScenario();
  const createStrategy = useCreateStrategyScenario();
  const [tab, setTab] = useState<StudioTab>("all");
  const [queryInput, setQueryInput] = useState("");
  const [pendingDelete, setPendingDelete] = useState<MyScenarioSummary | null>(
    null,
  );
  const query = useDebouncedValue(queryInput.trim(), STUDIO_SEARCH_DEBOUNCE_MS);
  const list = useMyScenarios(tab, query);
  const sentinelRef = useLoadMoreTrigger(
    list.fetchNextPage,
    list.hasNextPage && !list.isFetchingNextPage && !list.isNextPageError,
  );

  const handleNewStrategy = async (): Promise<void> => {
    try {
      const created = await createStrategy.mutateAsync();
      navigate(`/studio/${created.scenario_id}/edit`);
    } catch {
      showToast("Couldn't start a strategy scenario.", "error");
    }
  };

  const runDelete = async (scenario: MyScenarioSummary): Promise<void> => {
    try {
      await deleteScenario(scenario.scenario_id);
    } catch {
      const title = scenario.title.trim() || UNTITLED_SCENARIO_TITLE;
      showToast(`Couldn't delete “${title}”.`, "error", {
        label: "Retry",
        onClick: () => void runDelete(scenario),
      });
    }
  };

  const handleConfirmDelete = (scenario: MyScenarioSummary): void => {
    setPendingDelete(null);
    void runDelete(scenario);
  };

  const hasAnyScenarios = (list.statusCounts?.all ?? 0) > 0;
  const isEmpty = !list.isLoading && !list.isError && list.items.length === 0;

  return (
    <div className="mx-auto w-full max-w-[1440px] px-4 py-8 font-sans text-content md:px-6">
      <header className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div className="flex flex-col gap-1">
          <h1 className="font-display text-3xl font-semibold tracking-tight text-content md:text-5xl">
            Studio
          </h1>
          <p className="text-sm text-content-muted">
            Author, configure, and monitor your narrative worlds.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="secondary" onClick={() => navigate("/studio/stats")}>
            Stats
          </Button>
          <Button variant="secondary" disabled={createStrategy.isPending} onClick={handleNewStrategy}>
            New Strategy
          </Button>
          <Button variant="primary" onClick={() => navigate("/studio/new")}>
            New Story
          </Button>
        </div>
      </header>

      <div className="mt-8 flex flex-col gap-4">
        <StudioFilterBar
          tab={tab}
          onTabChange={setTab}
          query={queryInput}
          onQueryChange={setQueryInput}
          counts={list.statusCounts}
        />

        {list.isError && (
          <div className="flex min-h-[40vh] flex-col items-center justify-center gap-3">
            <p className="text-danger">Failed to load your scenarios.</p>
            <Button variant="secondary" onClick={list.refetch}>
              Retry
            </Button>
          </div>
        )}

        {isEmpty && (
          <StudioEmptyState
            tab={tab}
            query={query}
            hasAnyScenarios={hasAnyScenarios}
            onClearQuery={() => setQueryInput("")}
            onNewScenario={() => navigate("/studio/new")}
          />
        )}

        <ul className="flex flex-col gap-4">
          {list.isLoading && (
            <ScenarioRowSkeletonList count={FIRST_LOAD_SKELETON_COUNT} />
          )}
          {list.items.map((scenario) => (
            <StudioScenarioRow
              key={scenario.scenario_id}
              scenario={scenario}
              onDelete={setPendingDelete}
            />
          ))}
          {list.isFetchingNextPage && (
            <ScenarioRowSkeletonList count={NEXT_PAGE_SKELETON_COUNT} />
          )}
        </ul>

        {list.isNextPageError && (
          <div className="flex items-center justify-center gap-3 py-4">
            <p className="text-sm text-content-muted">Couldn't load more</p>
            <Button variant="secondary" size="sm" onClick={list.fetchNextPage}>
              Retry
            </Button>
          </div>
        )}
        <div ref={sentinelRef} aria-hidden="true" />
      </div>

      <DeleteScenarioDialog
        scenario={pendingDelete}
        onClose={() => setPendingDelete(null)}
        onConfirm={handleConfirmDelete}
      />
    </div>
  );
};
