import { create } from "zustand";
import {
  DEFAULT_DISCOVER_VIEW,
  DISCOVER_VIEW_STORAGE_KEY,
} from "../constants/discover.constants";
import type { DiscoverView } from "../types/discover.types";
import { logEvent } from "@/shared/lib/logger";

interface DiscoverViewState {
  view: DiscoverView;
  setView: (view: DiscoverView) => void;
}

function readStoredView(): DiscoverView {
  try {
    const stored = window.localStorage.getItem(DISCOVER_VIEW_STORAGE_KEY);
    return stored === "grid" || stored === "list"
      ? stored
      : DEFAULT_DISCOVER_VIEW;
  } catch (error) {
    logEvent("warning", "discover_view_preference_unreadable", { error: String(error) });
    return DEFAULT_DISCOVER_VIEW;
  }
}

function writeStoredView(view: DiscoverView): void {
  try {
    window.localStorage.setItem(DISCOVER_VIEW_STORAGE_KEY, view);
  } catch (error) {
    logEvent("warning", "discover_view_preference_not_saved", { error: String(error) });
  }
}

export const useDiscoverViewStore = create<DiscoverViewState>((set) => ({
  view: readStoredView(),
  setView: (view) => {
    writeStoredView(view);
    set({ view });
  },
}));
