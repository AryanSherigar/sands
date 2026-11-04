import React from "react";
import { IconMoon, IconSun } from "@tabler/icons-react";
import { useAppThemeStore } from "@/shared/stores/appTheme.store";

export const ThemeToggle: React.FC = () => {
  const { theme, toggleTheme } = useAppThemeStore();
  const isDark = theme === "dark";

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={isDark ? "Switch to light theme" : "Switch to dark theme"}
      className="flex h-9 w-9 items-center justify-center rounded-lg border border-border-subtle bg-surface-raised text-content transition-colors hover:bg-hover-wash focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-primary"
    >
      {isDark ? <IconSun size={18} /> : <IconMoon size={18} />}
    </button>
  );
};
