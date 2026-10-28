import { create } from "zustand";
import {
  DEFAULT_READER_FONT_SIZE,
  DEFAULT_READER_LINE_HEIGHT,
  DEFAULT_READER_THEME,
  READER_FONT_SIZES,
  READER_FONT_SIZE_STORAGE_KEY,
  READER_LINE_HEIGHTS,
  READER_LINE_HEIGHT_STORAGE_KEY,
  READER_THEMES,
  READER_THEME_STORAGE_KEY,
  REDUCE_SENSORY_EFFECTS_STORAGE_KEY,
} from "@/shared/constants/reader-preferences";
import { READER_FONT_STORAGE_KEY } from "@/shared/constants/narration-fonts";
import type {
  ReaderFontSize,
  ReaderLineHeight,
  ReaderTheme,
} from "@/shared/types/readerPreferences.types";
import { logEvent } from "@/shared/lib/logger";
import { prefersReducedMotion } from "@/shared/lib/prefersReducedMotion";

function readStorage(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch (error) {
    logEvent("warning", "reader_preferences_read_failed", { key, error: String(error) });
    return null;
  }
}

function writeStorage(key: string, value: string | null): boolean {
  try {
    if (value === null) {
      localStorage.removeItem(key);
    } else {
      localStorage.setItem(key, value);
    }
    return true;
  } catch (error) {
    logEvent("warning", "reader_preferences_write_failed", { key, error: String(error) });
    return false;
  }
}

function readTheme(): ReaderTheme {
  const stored = readStorage(READER_THEME_STORAGE_KEY);
  const match = READER_THEMES.find((theme) => theme === stored);
  return match ?? DEFAULT_READER_THEME;
}

function readFontSize(): ReaderFontSize {
  const stored = readStorage(READER_FONT_SIZE_STORAGE_KEY);
  const match = READER_FONT_SIZES.find((size) => size === stored);
  return match ?? DEFAULT_READER_FONT_SIZE;
}

function readLineHeight(): ReaderLineHeight {
  const stored = readStorage(READER_LINE_HEIGHT_STORAGE_KEY);
  const match = READER_LINE_HEIGHTS.find((height) => height === stored);
  return match ?? DEFAULT_READER_LINE_HEIGHT;
}

function readReduceSensoryEffects(): boolean {
  const stored = readStorage(REDUCE_SENSORY_EFFECTS_STORAGE_KEY);
  if (stored === "true") return true;
  if (stored === "false") return false;
  return prefersReducedMotion();
}

interface ReaderPreferencesState {
  fontId: string | null;
  theme: ReaderTheme;
  fontSize: ReaderFontSize;
  lineHeight: ReaderLineHeight;
  reduceSensoryEffects: boolean;
  hasStorageError: boolean;
  persistAll: () => void;
  setFontId: (fontId: string | null) => void;
  setTheme: (theme: ReaderTheme) => void;
  setFontSize: (fontSize: ReaderFontSize) => void;
  setLineHeight: (lineHeight: ReaderLineHeight) => void;
  setReduceSensoryEffects: (reduceSensoryEffects: boolean) => void;
}

export const useReaderPreferencesStore = create<ReaderPreferencesState>(
  (set, get) => ({
    fontId: readStorage(READER_FONT_STORAGE_KEY),
    theme: readTheme(),
    fontSize: readFontSize(),
    lineHeight: readLineHeight(),
    reduceSensoryEffects: readReduceSensoryEffects(),
    hasStorageError: false,
    persistAll: () => {
      const { fontId, theme, fontSize, lineHeight, reduceSensoryEffects } = get();
      const results = [
        writeStorage(READER_FONT_STORAGE_KEY, fontId),
        writeStorage(READER_THEME_STORAGE_KEY, theme),
        writeStorage(READER_FONT_SIZE_STORAGE_KEY, fontSize),
        writeStorage(READER_LINE_HEIGHT_STORAGE_KEY, lineHeight),
        writeStorage(
          REDUCE_SENSORY_EFFECTS_STORAGE_KEY,
          String(reduceSensoryEffects),
        ),
      ];
      set({ hasStorageError: results.includes(false) });
    },
    setFontId: (fontId) => {
      const isSaved = writeStorage(READER_FONT_STORAGE_KEY, fontId);
      set({ fontId, hasStorageError: !isSaved });
    },
    setTheme: (theme) => {
      const isSaved = writeStorage(READER_THEME_STORAGE_KEY, theme);
      set({ theme, hasStorageError: !isSaved });
    },
    setFontSize: (fontSize) => {
      const isSaved = writeStorage(READER_FONT_SIZE_STORAGE_KEY, fontSize);
      set({ fontSize, hasStorageError: !isSaved });
    },
    setLineHeight: (lineHeight) => {
      const isSaved = writeStorage(READER_LINE_HEIGHT_STORAGE_KEY, lineHeight);
      set({ lineHeight, hasStorageError: !isSaved });
    },
    setReduceSensoryEffects: (reduceSensoryEffects) => {
      const isSaved = writeStorage(
        REDUCE_SENSORY_EFFECTS_STORAGE_KEY,
        String(reduceSensoryEffects),
      );
      set({ reduceSensoryEffects, hasStorageError: !isSaved });
    },
  }),
);
