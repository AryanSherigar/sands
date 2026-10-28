import { useCallback } from "react";
import { buildCardTabId } from "../lib/studioTabs";
import { useStudioTabsStore } from "../stores/studioTabs.store";

export const useOpenCardTab = () => {
  const openTab = useStudioTabsStore((state) => state.openTab);
  return useCallback(
    (entityId: string): void => openTab(buildCardTabId(entityId)),
    [openTab],
  );
};
