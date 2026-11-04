import { create } from "zustand";
import { logEvent } from "@/shared/lib/logger";

export type AppTheme = "light" | "dark";

export const APP_THEME_STORAGE_KEY = "sands_app_theme";

interface AppThemeState {
  theme: AppTheme;
  setTheme: (theme: AppTheme) => void;
  toggleTheme: () => void;
}

function readStoredTheme(): AppTheme {
  try {
    const stored = localStorage.getItem(APP_THEME_STORAGE_KEY);
    return stored === "dark" ? "dark" : "light";
  } catch (error) {
    logEvent("warning", "app_theme_read_failed", { error: String(error) });
    return "light";
  }
}

function applyThemeToDOM(theme: AppTheme): void {
  try {
    if (typeof document !== "undefined") {
      document.documentElement.classList.toggle("dark", theme === "dark");
    }
  } catch (error) {
    logEvent("warning", "app_theme_dom_toggle_failed", { error: String(error) });
  }
}

function persistTheme(theme: AppTheme): void {
  try {
    localStorage.setItem(APP_THEME_STORAGE_KEY, theme);
  } catch (error) {
    logEvent("warning", "app_theme_write_failed", { error: String(error) });
  }
}

const initialTheme = readStoredTheme();
applyThemeToDOM(initialTheme);

export const useAppThemeStore = create<AppThemeState>((set, get) => ({
  theme: initialTheme,
  setTheme: (theme: AppTheme) => {
    persistTheme(theme);
    applyThemeToDOM(theme);
    set({ theme });
  },
  toggleTheme: () => {
    const nextTheme: AppTheme = get().theme === "dark" ? "light" : "dark";
    persistTheme(nextTheme);
    applyThemeToDOM(nextTheme);
    set({ theme: nextTheme });
  },
}));
