import { beforeEach, describe, expect, it } from "vitest";
import {
  APP_THEME_STORAGE_KEY,
  useAppThemeStore,
} from "../appTheme.store";

describe("appTheme.store", () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.classList.remove("dark");
    useAppThemeStore.setState({ theme: "light" });
  });

  it("defaults to light theme when localStorage is empty", () => {
    expect(useAppThemeStore.getState().theme).toBe("light");
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });

  it("switches theme to dark and syncs DOM class and storage", () => {
    useAppThemeStore.getState().setTheme("dark");
    expect(useAppThemeStore.getState().theme).toBe("dark");
    expect(localStorage.getItem(APP_THEME_STORAGE_KEY)).toBe("dark");
    expect(document.documentElement.classList.contains("dark")).toBe(true);
  });

  it("switches theme to light and removes dark class from DOM", () => {
    useAppThemeStore.getState().setTheme("dark");
    expect(document.documentElement.classList.contains("dark")).toBe(true);

    useAppThemeStore.getState().setTheme("light");
    expect(useAppThemeStore.getState().theme).toBe("light");
    expect(localStorage.getItem(APP_THEME_STORAGE_KEY)).toBe("light");
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });

  it("toggles theme back and forth", () => {
    useAppThemeStore.getState().toggleTheme();
    expect(useAppThemeStore.getState().theme).toBe("dark");
    expect(document.documentElement.classList.contains("dark")).toBe(true);

    useAppThemeStore.getState().toggleTheme();
    expect(useAppThemeStore.getState().theme).toBe("light");
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });

  it("handles storage exceptions gracefully", () => {
    const originalSetItem = localStorage.setItem;
    localStorage.setItem = () => {
      throw new Error("QuotaExceededError");
    };

    expect(() => {
      useAppThemeStore.getState().setTheme("dark");
    }).not.toThrow();

    expect(useAppThemeStore.getState().theme).toBe("dark");
    expect(document.documentElement.classList.contains("dark")).toBe(true);

    localStorage.setItem = originalSetItem;
  });
});
