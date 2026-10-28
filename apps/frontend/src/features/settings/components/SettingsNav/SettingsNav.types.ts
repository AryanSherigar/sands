type SettingsNavOrientation = "horizontal" | "vertical";

interface SettingsNavSection {
  id: string;
  label: string;
}

export interface SettingsNavProps {
  sections: readonly SettingsNavSection[];
  orientation?: SettingsNavOrientation;
}
