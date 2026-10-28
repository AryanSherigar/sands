import type { ExtraDefinition } from "../../constants/extras";

export interface StudioFrameProps {
  scenarioId: string | null;
  onDraftCreated: (scenarioId: string) => void;
}

export interface ExtraEditorPanelProps {
  extra: ExtraDefinition;
}

export interface ExtraEditorProps {
  scenarioId: string;
  canEnableComposure?: boolean;
}

export interface StudioTabPanelProps {
  tabId: string;
}
