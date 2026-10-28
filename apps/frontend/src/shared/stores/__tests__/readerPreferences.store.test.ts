import { describe, it, expect, beforeEach, vi } from "vitest";
import { useReaderPreferencesStore } from "../readerPreferences.store";
import {
  DEFAULT_READER_FONT_SIZE,
  DEFAULT_READER_LINE_HEIGHT,
  DEFAULT_READER_THEME,
  READER_FONT_SIZE_STORAGE_KEY,
  READER_LINE_HEIGHT_STORAGE_KEY,
  READER_THEME_STORAGE_KEY,
  REDUCE_SENSORY_EFFECTS_STORAGE_KEY,
} from "@/shared/constants/reader-preferences";
import { READER_FONT_STORAGE_KEY } from "@/shared/constants/narration-fonts";

describe("readerPreferences.store", () => {
  beforeEach(() => {
    localStorage.clear();
    useReaderPreferencesStore.setState({
      fontId: null,
      theme: DEFAULT_READER_THEME,
      fontSize: DEFAULT_READER_FONT_SIZE,
      lineHeight: DEFAULT_READER_LINE_HEIGHT,
      reduceSensoryEffects: false,
      hasStorageError: false,
    });
  });

  describe("reduce sensory effects", () => {
    it("persists the switch to storage", () => {
      useReaderPreferencesStore.getState().setReduceSensoryEffects(true);

      expect(useReaderPreferencesStore.getState().reduceSensoryEffects).toBe(true);
      expect(localStorage.getItem(REDUCE_SENSORY_EFFECTS_STORAGE_KEY)).toBe("true");
    });

    it("is saved by persistAll", () => {
      useReaderPreferencesStore.setState({ reduceSensoryEffects: true });

      useReaderPreferencesStore.getState().persistAll();

      expect(localStorage.getItem(REDUCE_SENSORY_EFFECTS_STORAGE_KEY)).toBe("true");
    });
  });

  describe("font size settings", () => {
    it("updates font size to small and persists to storage", () => {
      useReaderPreferencesStore.getState().setFontSize("small");

      expect(useReaderPreferencesStore.getState().fontSize).toBe("small");
      expect(localStorage.getItem(READER_FONT_SIZE_STORAGE_KEY)).toBe("small");
    });

    it("updates font size to large and persists to storage", () => {
      useReaderPreferencesStore.getState().setFontSize("large");

      expect(useReaderPreferencesStore.getState().fontSize).toBe("large");
      expect(localStorage.getItem(READER_FONT_SIZE_STORAGE_KEY)).toBe("large");
    });

    it("updates font size to extra-large and persists to storage", () => {
      useReaderPreferencesStore.getState().setFontSize("extra-large");

      expect(useReaderPreferencesStore.getState().fontSize).toBe("extra-large");
      expect(localStorage.getItem(READER_FONT_SIZE_STORAGE_KEY)).toBe("extra-large");
    });
  });

  describe("line height modes", () => {
    it("updates line height to compact and persists to storage", () => {
      useReaderPreferencesStore.getState().setLineHeight("compact");

      expect(useReaderPreferencesStore.getState().lineHeight).toBe("compact");
      expect(localStorage.getItem(READER_LINE_HEIGHT_STORAGE_KEY)).toBe("compact");
    });

    it("updates line height to comfortable and persists to storage", () => {
      useReaderPreferencesStore.getState().setLineHeight("comfortable");

      expect(useReaderPreferencesStore.getState().lineHeight).toBe("comfortable");
      expect(localStorage.getItem(READER_LINE_HEIGHT_STORAGE_KEY)).toBe("comfortable");
    });

    it("updates line height to relaxed and persists to storage", () => {
      useReaderPreferencesStore.getState().setLineHeight("relaxed");

      expect(useReaderPreferencesStore.getState().lineHeight).toBe("relaxed");
      expect(localStorage.getItem(READER_LINE_HEIGHT_STORAGE_KEY)).toBe("relaxed");
    });
  });

  describe("theme switching", () => {
    it("switches theme to antique-sepia and persists to storage", () => {
      useReaderPreferencesStore.getState().setTheme("antique-sepia");

      expect(useReaderPreferencesStore.getState().theme).toBe("antique-sepia");
      expect(localStorage.getItem(READER_THEME_STORAGE_KEY)).toBe("antique-sepia");
    });

    it("switches theme to dark-velvet and persists to storage", () => {
      useReaderPreferencesStore.getState().setTheme("dark-velvet");

      expect(useReaderPreferencesStore.getState().theme).toBe("dark-velvet");
      expect(localStorage.getItem(READER_THEME_STORAGE_KEY)).toBe("dark-velvet");
    });
  });

  describe("font id and persistence", () => {
    it("updates fontId and persists to storage", () => {
      useReaderPreferencesStore.getState().setFontId("lora");

      expect(useReaderPreferencesStore.getState().fontId).toBe("lora");
      expect(localStorage.getItem(READER_FONT_STORAGE_KEY)).toBe("lora");
    });

    it("removes fontId when set to null", () => {
      localStorage.setItem(READER_FONT_STORAGE_KEY, "lora");
      useReaderPreferencesStore.getState().setFontId(null);

      expect(useReaderPreferencesStore.getState().fontId).toBeNull();
      expect(localStorage.getItem(READER_FONT_STORAGE_KEY)).toBeNull();
    });

    it("persists all current settings with persistAll", () => {
      useReaderPreferencesStore.setState({
        fontId: "cinzel",
        theme: "antique-sepia",
        fontSize: "extra-large",
        lineHeight: "relaxed",
      });

      useReaderPreferencesStore.getState().persistAll();

      expect(localStorage.getItem(READER_FONT_STORAGE_KEY)).toBe("cinzel");
      expect(localStorage.getItem(READER_THEME_STORAGE_KEY)).toBe("antique-sepia");
      expect(localStorage.getItem(READER_FONT_SIZE_STORAGE_KEY)).toBe("extra-large");
      expect(localStorage.getItem(READER_LINE_HEIGHT_STORAGE_KEY)).toBe("relaxed");
      expect(useReaderPreferencesStore.getState().hasStorageError).toBe(false);
    });

    it("flags hasStorageError when writing to storage fails", () => {
      const setItemSpy = vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
        throw new Error("Quota exceeded");
      });

      useReaderPreferencesStore.getState().setFontSize("small");

      expect(useReaderPreferencesStore.getState().hasStorageError).toBe(true);
      setItemSpy.mockRestore();
    });
  });
});
