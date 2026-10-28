import { create } from "zustand";

interface ProfilePreviewState {
  isPreviewingAsVisitor: boolean;
  setPreviewingAsVisitor: (isPreviewing: boolean) => void;
}

export const useProfilePreviewStore = create<ProfilePreviewState>((set) => ({
  isPreviewingAsVisitor: false,
  setPreviewingAsVisitor: (isPreviewing) =>
    set({ isPreviewingAsVisitor: isPreviewing }),
}));
