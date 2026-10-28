import React from "react";
import { Button } from "@/shared/components/ui/Button";
import { useMediaQuery } from "@/shared/hooks/useMediaQuery";
import {
  CHAT_COLUMN_CLASS,
  CHAT_OVERLAY_CLASS,
  CHAT_SHEET_CLASS,
  MOBILE_MEDIA_QUERY,
  WIDE_MEDIA_QUERY,
} from "../../constants/studioFrame";
import { GUIDE_TAB_ID } from "../../constants/studioTabs";
import { useStudioTabsStore } from "../../stores/studioTabs.store";
import { StudioChatColumn } from "./StudioChatColumn";
import { StudioTabPanel } from "./StudioTabPanel";

const pickChatClass = (isMobile: boolean, shouldOverlay: boolean): string => {
  if (isMobile) return CHAT_SHEET_CLASS;
  return shouldOverlay ? CHAT_OVERLAY_CLASS : CHAT_COLUMN_CLASS;
};

export const StudioPanels: React.FC = () => {
  const isMobile = useMediaQuery(MOBILE_MEDIA_QUERY);
  const isWide = useMediaQuery(WIDE_MEDIA_QUERY);
  const isChatOpen = useStudioTabsStore((state) => state.isChatOpen);
  const activeTabId = useStudioTabsStore((state) => state.activeTabId);
  const splitTabId = useStudioTabsStore((state) => state.splitTabId);
  const openTab = useStudioTabsStore((state) => state.openTab);
  const shownSplitId = isMobile ? null : splitTabId;
  const shouldOverlayChat = !isWide && Boolean(shownSplitId);

  const chat = isChatOpen && (
    <StudioChatColumn className={pickChatClass(isMobile, shouldOverlayChat)} />
  );

  if (!activeTabId) {
    return (
      <div className="relative flex min-h-0 flex-1">
        <div className="flex flex-1 flex-col items-center justify-center gap-3 p-8 text-center">
          <p className="text-meta text-content-muted">Nothing is open.</p>
          <Button type="button" variant="secondary" onClick={() => openTab(GUIDE_TAB_ID)}>
            Open Guide
          </Button>
        </div>
        {chat}
      </div>
    );
  }

  return (
    <div className="relative flex min-h-0 flex-1">
      <section aria-label="Active tab" className="min-w-0 flex-1 overflow-y-auto">
        <StudioTabPanel tabId={activeTabId} />
      </section>
      {shownSplitId && (
        <section
          aria-label="Split tab"
          className="min-w-0 flex-1 overflow-y-auto border-l border-border-subtle"
        >
          <StudioTabPanel tabId={shownSplitId} />
        </section>
      )}
      {chat}
    </div>
  );
};
