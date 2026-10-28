import React from "react";
import { IconX } from "@tabler/icons-react";
import { CHAT_BUTTON_LABEL } from "../../constants/studioFrame";
import { useGuide } from "../../hooks/useGuide";
import { useScopedChatBinding } from "../../hooks/useScopedChatBinding";
import { useStudioTabsStore } from "../../stores/studioTabs.store";
import { AIChatSidebar } from "../AIChatSidebar/AIChatSidebar";

export const StudioChatColumn: React.FC<{ className: string }> = ({ className }) => {
  const { scenarioId } = useGuide();
  const binding = useScopedChatBinding();
  const setChatOpen = useStudioTabsStore((state) => state.setChatOpen);

  return (
    <aside aria-label={CHAT_BUTTON_LABEL} className={className}>
      <div className="flex shrink-0 items-center justify-between border-b border-border-subtle px-3 py-2">
        <h2 className="text-meta font-medium text-content">{CHAT_BUTTON_LABEL}</h2>
        <button
          type="button"
          aria-label="Close Chat"
          onClick={() => setChatOpen(false)}
          className="text-content-faint transition-colors hover:text-content"
        >
          <IconX size={16} aria-hidden="true" />
        </button>
      </div>
      <div className="min-h-0 flex-1">
        <AIChatSidebar scenarioId={scenarioId ?? undefined} scopedTab={binding} />
      </div>
    </aside>
  );
};
