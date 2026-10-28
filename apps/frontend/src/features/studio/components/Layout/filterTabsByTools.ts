import type { ToolKey } from "@/shared/constants/scenario-tools";

export const isTabAvailable = (
  tab: { tool?: ToolKey },
  enabledTools: readonly string[],
): boolean => tab.tool === undefined || enabledTools.includes(tab.tool);

export const filterTabsByTools = <T extends { tool?: ToolKey }>(
  tabs: readonly T[],
  enabledTools: readonly string[],
): T[] => tabs.filter((tab) => isTabAvailable(tab, enabledTools));
