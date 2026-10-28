import { useMediaQuery } from "@/shared/hooks/useMediaQuery";
import { MOBILE_MEDIA_QUERY } from "../constants/studioFrame";
import { PLAYTEST_TAB_ID } from "../constants/studioTabs";
import { useStudioTabsStore } from "../stores/studioTabs.store";

export const useOpenPlaytestTab = (): (() => void) => {
  const isMobile = useMediaQuery(MOBILE_MEDIA_QUERY);
  const openTab = useStudioTabsStore((state) => state.openTab);

  return () => openTab(PLAYTEST_TAB_ID, { isSplit: !isMobile });
};
