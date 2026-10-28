export interface StudioTabItemProps {
  tabId: string;
  label: string;
  isActive: boolean;
  isSplit: boolean;
  isSaving: boolean;
}

export interface TabLabelResolver {
  (tabId: string): string;
}
