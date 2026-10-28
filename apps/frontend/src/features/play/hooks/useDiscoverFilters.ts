import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { useAuthStore } from "@/features/auth/stores/auth.store";
import { useMaturePreference } from "@/shared/hooks/useMaturePreference";
import { useToast } from "@/shared/hooks/useToast";
import type { DiscoverFilters } from "../types/discover.types";
import {
  parseDiscoverFilters,
  serializeDiscoverFilters,
} from "../utils/discoverFilters";

export interface UseDiscoverFiltersResult {
  filters: DiscoverFilters;
  setFilters: (next: DiscoverFilters) => void;
}

export const useDiscoverFilters = (): UseDiscoverFiltersResult => {
  const [searchParams, setSearchParams] = useSearchParams();
  const isSignedIn = useAuthStore((state) => state.isAuthenticated);
  const { isEnabled: isMatureSaved, setEnabled } = useMaturePreference();
  const showToast = useToast();
  const filters = useMemo(
    () => parseDiscoverFilters(searchParams, isMatureSaved),
    [searchParams, isMatureSaved],
  );

  const applyFilters = useCallback(
    (next: DiscoverFilters): void => {
      setSearchParams(serializeDiscoverFilters(next, isMatureSaved), {
        replace: true,
      });
    },
    [setSearchParams, isMatureSaved],
  );

  const persistMature = useCallback(
    async (next: DiscoverFilters): Promise<void> => {
      const result = await setEnabled(next.isMatureIncluded);
      if (result.errorMessage) showToast(result.errorMessage, "error");
      if (result.isApplied || !next.isMatureIncluded) applyFilters(next);
    },
    [setEnabled, showToast, applyFilters],
  );

  const setFilters = useCallback(
    (next: DiscoverFilters): void => {
      const isMatureChange = next.isMatureIncluded !== filters.isMatureIncluded;
      if (isSignedIn && isMatureChange) {
        void persistMature(next);
        return;
      }
      applyFilters(next);
    },
    [isSignedIn, filters.isMatureIncluded, persistMature, applyFilters],
  );

  return { filters, setFilters };
};
