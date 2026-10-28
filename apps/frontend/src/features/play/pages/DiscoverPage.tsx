import React, { useCallback, useState } from "react";
import { useIsAuthenticated } from "@/shared/hooks/useIsAuthenticated";
import { useRequireAuth } from "@/shared/hooks/useRequireAuth";
import { DiscoverEmptyState } from "../components/Discover/DiscoverEmptyState";
import { DiscoverLayout } from "../components/Discover/DiscoverLayout";
import { DiscoverResults } from "../components/Discover/DiscoverResults";
import { FilterSheet } from "../components/Discover/FilterSheet";
import { FilterSidebar } from "../components/Discover/FilterSidebar";
import { MobileFilterBar } from "../components/Discover/MobileFilterBar";
import { ResultsHeader } from "../components/Discover/ResultsHeader";
import { useDiscoverFilters } from "../hooks/useDiscoverFilters";
import { useScenarioList } from "../hooks/useScenarioList";
import { useSurpriseMe } from "../hooks/useSurpriseMe";
import { useToggleSave } from "../hooks/useToggleSave";
import { useDiscoverViewStore } from "../stores/discoverView.store";
import {
  buildActiveFilterChips,
  clearAllFilters,
  removeFilterByChipId,
} from "../utils/discoverFilters";

const useDiscoverPageState = () => {
  const { filters, setFilters } = useDiscoverFilters();
  const list = useScenarioList(filters);
  const view = useDiscoverViewStore((state) => state.view);
  const setView = useDiscoverViewStore((state) => state.setView);
  const isAuthenticated = useIsAuthenticated();
  const requireAuth = useRequireAuth("save");
  const toggleSave = useToggleSave();
  const surprise = useSurpriseMe(list.items);
  const [isSheetOpen, setIsSheetOpen] = useState(false);

  const chips = buildActiveFilterChips(filters);
  const hasActiveFilters = chips.length > 0 || filters.query !== "";
  const handleSignIn = useCallback((): void => void requireAuth(), [requireAuth]);
  const handleClearAll = (): void => setFilters(clearAllFilters(filters));
  const handleGenreToggle = (genre: string): void => {
    const isSelected = filters.genres.includes(genre);
    const nextGenres = isSelected
      ? filters.genres.filter((item) => item !== genre)
      : [...filters.genres, genre];
    setFilters({ ...filters, genres: nextGenres });
  };

  return {
    filters,
    setFilters,
    list,
    view,
    setView,
    isAuthenticated,
    toggleSave,
    surprise,
    isSheetOpen,
    setIsSheetOpen,
    chips,
    hasActiveFilters,
    handleSignIn,
    handleClearAll,
    handleGenreToggle,
  };
};

export const DiscoverPage: React.FC = () => {
  const state = useDiscoverPageState();

  const handleRemoveChip = (chipId: string) => {
    state.setFilters(removeFilterByChipId(state.filters, chipId));
  };

  const handleSortChange = (sort: typeof state.filters.sort) => {
    state.setFilters({ ...state.filters, sort });
  };

  const handleExploreTopRated = () => {
    state.setFilters({ ...clearAllFilters(state.filters), sort: "top" });
  };

  return (
    <DiscoverLayout
      sidebar={
        <FilterSidebar
          filters={state.filters}
          hasActiveFilters={state.hasActiveFilters}
          isAuthenticated={state.isAuthenticated}
          isSurpriseDisabled={state.surprise.isDisabled}
          onChange={state.setFilters}
          onClearAll={state.handleClearAll}
          onSignIn={state.handleSignIn}
          onSurprise={state.surprise.handleSurprise}
        />
      }
    >
      <MobileFilterBar
        selectedGenres={state.filters.genres}
        activeFilterCount={state.chips.length}
        onToggleGenre={state.handleGenreToggle}
        onOpenFilters={() => state.setIsSheetOpen(true)}
      />
      <ResultsHeader
        query={state.filters.query}
        totalCount={state.list.totalCount}
        chips={state.chips}
        sort={state.filters.sort}
        view={state.view}
        onRemoveChip={handleRemoveChip}
        onClearAll={state.handleClearAll}
        onSortChange={handleSortChange}
        onViewChange={state.setView}
      />
      <DiscoverResults
        list={state.list}
        view={state.view}
        onToggleSave={(scenario) => void state.toggleSave(scenario)}
        emptyState={
          <DiscoverEmptyState
            filters={state.filters}
            hasActiveFilters={state.hasActiveFilters}
            onClearFilters={state.handleClearAll}
            onExploreTopRated={handleExploreTopRated}
          />
        }
      />
      <FilterSheet
        isOpen={state.isSheetOpen}
        appliedFilters={state.filters}
        isAuthenticated={state.isAuthenticated}
        onApply={state.setFilters}
        onClose={() => state.setIsSheetOpen(false)}
        onSignIn={state.handleSignIn}
      />
    </DiscoverLayout>
  );
};
