import { create } from "zustand";
import { MasterModeTabId } from "../components/Layout/MasterModeStudioLayout.types";
import {
  SetupInputField,
  SetupInputOption,
  SetupInputType,
} from "@/shared/types/scenario.types";

export type { SetupInputField, SetupInputOption, SetupInputType };

interface StudioState {
  lastSaved: Date | null;
  isSaving: boolean;
  setSaveState: (isSaving: boolean, lastSaved?: Date) => void;
  resetSaveState: () => void;

  hasEditConflict: boolean;
  setHasEditConflict: (hasEditConflict: boolean) => void;

  activeMasterTab: MasterModeTabId;
  setActiveMasterTab: (tab: MasterModeTabId) => void;

  factsEntityFilter: string | null;
  setFactsEntityFilter: (entityId: string | null) => void;
}

export const useStudioStore = create<StudioState>((set) => ({
  lastSaved: null,
  isSaving: false,
  setSaveState: (isSaving, lastSaved) =>
    set((state) => ({
      isSaving,
      lastSaved: lastSaved !== undefined ? lastSaved : state.lastSaved,
    })),
  resetSaveState: () => set({ lastSaved: null, isSaving: false }),

  hasEditConflict: false,
  setHasEditConflict: (hasEditConflict) => set({ hasEditConflict }),

  activeMasterTab: "entities",
  setActiveMasterTab: (tab) => set({ activeMasterTab: tab }),

  factsEntityFilter: null,
  setFactsEntityFilter: (entityId) => set({ factsEntityFilter: entityId }),
}));
