import React from "react";
import { SCOPED_EMPTY_TAB_NOTE, SCOPED_NEW_CHAT_LABEL } from "../../constants/scopedChat";
import type { ScopedChatContext } from "../../types/scopedChat.types";

export interface ScopedChatHeaderProps {
  context: ScopedChatContext;
  onNewChat: () => void;
}

const buildSeesLine = (tabLabel: string): string =>
  tabLabel ? `Chat sees: ${tabLabel} + your one line idea.` : "Chat sees: your one line idea.";

export const ScopedChatHeader: React.FC<ScopedChatHeaderProps> = ({ context, onNewChat }) => {
  const isTabEmpty = context.tabText.trim().length === 0;
  return (
    <div className="flex items-start justify-between gap-3 border-b border-border-subtle px-3 py-2">
      <div className="min-w-0 space-y-0.5">
        <p className="text-meta text-content">{buildSeesLine(context.tabLabel)}</p>
        {isTabEmpty && context.tabLabel && (
          <p className="text-micro text-content-faint">{SCOPED_EMPTY_TAB_NOTE}</p>
        )}
      </div>
      <button
        type="button"
        onClick={onNewChat}
        className="shrink-0 rounded-md px-2 py-1 text-micro text-content-muted transition-colors hover:text-content focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-primary/30"
      >
        {SCOPED_NEW_CHAT_LABEL}
      </button>
    </div>
  );
};
