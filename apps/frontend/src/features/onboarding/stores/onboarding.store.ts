import { create } from "zustand";
import { useReaderPreferencesStore } from "@/shared/stores/readerPreferences.store";
import type {
  ReaderFontSize,
  ReaderLineHeight,
  ReaderTheme,
} from "@/shared/types/readerPreferences.types";
import { MAX_PREFERRED_GENRES } from "../constants/onboarding.constants";
import type { OnboardingDraft, OnboardingStepId } from "../types/onboarding.types";

interface OnboardingState extends OnboardingDraft {
  step: OnboardingStepId;
  goToStep: (step: OnboardingStepId) => void;
  toggleGenre: (genre: string) => void;
  setDisplayName: (displayName: string) => void;
  setBio: (bio: string) => void;
  setAvatarUrl: (avatarUrl: string) => void;
  setBannerUrl: (bannerUrl: string) => void;
  setReaderTheme: (theme: ReaderTheme) => void;
  setReaderFontId: (fontId: string | null) => void;
  setReaderFontSize: (fontSize: ReaderFontSize) => void;
  setReaderLineHeight: (lineHeight: ReaderLineHeight) => void;
  reset: (displayName: string) => void;
  hydrate: (draft: Partial<OnboardingDraft>) => void;
}

function buildInitialDraft(displayName: string): OnboardingDraft {
  const reader = useReaderPreferencesStore.getState();
  return {
    genres: [],
    displayName,
    bio: "",
    avatarUrl: null,
    bannerUrl: null,
    readerTheme: reader.theme,
    readerFontId: reader.fontId,
    readerFontSize: reader.fontSize,
    readerLineHeight: reader.lineHeight,
  };
}

function nextGenres(current: string[], genre: string): string[] {
  if (current.includes(genre)) {
    return current.filter((selected) => selected !== genre);
  }
  if (current.length >= MAX_PREFERRED_GENRES) return current;
  return [...current, genre];
}

export const useOnboardingStore = create<OnboardingState>((set) => ({
  step: "welcome",
  ...buildInitialDraft(""),
  goToStep: (step) => set({ step }),
  toggleGenre: (genre) =>
    set((state) => ({ genres: nextGenres(state.genres, genre) })),
  setDisplayName: (displayName) => set({ displayName }),
  setBio: (bio) => set({ bio }),
  setAvatarUrl: (avatarUrl) => set({ avatarUrl }),
  setBannerUrl: (bannerUrl) => set({ bannerUrl }),
  setReaderTheme: (readerTheme) => set({ readerTheme }),
  setReaderFontId: (readerFontId) => set({ readerFontId }),
  setReaderFontSize: (readerFontSize) => set({ readerFontSize }),
  setReaderLineHeight: (readerLineHeight) => set({ readerLineHeight }),
  reset: (displayName) => set({ step: "welcome", ...buildInitialDraft(displayName) }),
  hydrate: (draft) => set(draft),
}));
