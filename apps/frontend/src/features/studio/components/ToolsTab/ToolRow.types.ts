import { ScenarioToolDefinition } from "@/shared/constants/scenario-tools";

export interface ToolRowProps {
  tool: ScenarioToolDefinition;
  isEnabled: boolean;
  isBusy: boolean;
  blockedBy: string[];
  inertCount: number;
  onToggle: (toolKey: string, shouldEnable: boolean) => void;
}
