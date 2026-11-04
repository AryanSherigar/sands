import React from "react";
import { useAppThemeStore, type AppTheme } from "@/shared/stores/appTheme.store";
import { OptionGroup } from "../OptionGroup/OptionGroup";

const THEME_OPTIONS = [
  { value: "light", label: "Light (Wilds Atmosphere)" },
  { value: "dark", label: "Dark (Velvet Noir)" },
];

export const AppearanceSection: React.FC = () => {
  const { theme, setTheme } = useAppThemeStore();

  return (
    <div className="space-y-5 rounded-md border border-border-subtle bg-surface-raised p-5">
      <OptionGroup
        label="Interface theme"
        options={THEME_OPTIONS}
        value={theme}
        onChange={(val) => setTheme(val as AppTheme)}
      />
    </div>
  );
};
