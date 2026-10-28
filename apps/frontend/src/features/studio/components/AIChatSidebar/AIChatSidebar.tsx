import React, { useEffect, useRef, useState } from "react";
import { useAssistantChat } from "../../hooks/useAssistantChat";
import { useScopedProposals } from "../../hooks/useScopedProposals";
import type { ScopedTabBinding } from "../../types/scopedChat.types";
import { useMasterActionApplier } from "../../hooks/useMasterActionApplier";
import {
  ActionBlock,
  ACTION_TARGET_LABELS,
  DestructiveConfirmState,
  isDeleteActionBlock,
  MASTER_EXPRESSION_TARGETS,
} from "../../types/assistant.types";
import { ActionCard } from "./ActionCard";
import { ConflictModal } from "./ConflictModal";
import { DestructiveConfirmModal } from "./DestructiveConfirmModal";
import {
  ExpressionReviewModal,
  ExpressionReviewTarget,
} from "./ExpressionReviewModal";
import { QuickPromptChips } from "./QuickPromptChips";
import { ScopedChatHeader } from "./ScopedChatHeader";
import { ScopedProposalCard } from "./ScopedProposalCard";
import { parseMessageSegments, MessageSegment } from "./parseActionBlocks";

export interface AIChatSidebarProps {
  activeSection?: string;
  scenarioId?: string;
  scopedTab?: ScopedTabBinding;
}

const INITIAL_DESTRUCTIVE_STATE: DestructiveConfirmState = {
  isOpen: false,
  block: null,
  description: "",
};

interface ReviewState {
  target: ExpressionReviewTarget;
  draft: Record<string, unknown> | null;
  key: string;
}

const parseJsonSafe = (content: string): Record<string, unknown> | null => {
  try {
    return JSON.parse(content);
  } catch {
    return null;
  }
};

export const AIChatSidebar: React.FC<AIChatSidebarProps> = ({
  activeSection = "meta",
  scenarioId,
  scopedTab,
}) => {
  const [input, setInput] = useState("");
  const [destructiveState, setDestructiveState] =
    useState<DestructiveConfirmState>(INITIAL_DESTRUCTIVE_STATE);
  const [reviewState, setReviewState] = useState<ReviewState | null>(null);
  const [appliedKeys, setAppliedKeys] = useState<Set<string>>(new Set());
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const mode = scopedTab ? "scoped" : "master";
  const {
    messages,
    isStreaming,
    sendMessage,
    clearChat,
    stopGeneration,
    reportApplyError,
    blockValidationByMessage,
  } = useAssistantChat(
    activeSection,
    mode,
    scenarioId ?? null,
    scopedTab?.context ?? null,
  );
  const scopedProposals = useScopedProposals(scopedTab, reportApplyError);
  const [isConfirmingClear, setIsConfirmingClear] = useState(false);
  const masterApplier = useMasterActionApplier(
    scenarioId ?? null,
    reportApplyError,
  );

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView?.({ behavior: "smooth" });
  }, [messages]);

  const handleSend = () => {
    if (!input.trim() || isStreaming) return;
    sendMessage(input);
    setInput("");
    setIsConfirmingClear(false);
  };

  const markApplied = (key: string) =>
    setAppliedKeys((prev) => new Set(prev).add(key));

  const buildDestructiveDescription = (block: ActionBlock): string => {
    const label = ACTION_TARGET_LABELS[block.target] || block.target;
    return `This will permanently delete this ${label.toLowerCase()} from your scenario. This cannot be undone.`;
  };

  const handleMasterApplyBlock = async (block: ActionBlock, key: string) => {
    if (isDeleteActionBlock(block)) {
      setDestructiveState({
        isOpen: true,
        block,
        description: buildDestructiveDescription(block),
      });
      return;
    }
    if (MASTER_EXPRESSION_TARGETS.includes(block.target)) {
      setReviewState({
        target: block.target as ExpressionReviewTarget,
        draft: parseJsonSafe(block.content),
        key,
      });
      return;
    }
    await masterApplier.applyBlock(block);
    markApplied(key);
  };

  const handleApplyBlock = (block: ActionBlock, key: string) => {
    void handleMasterApplyBlock(block, key);
  };

  const handleApplyAll = async (
    blocks: { block: ActionBlock; key: string }[],
  ) => {
    const applicable = blocks.filter(
      (b) =>
        !isDeleteActionBlock(b.block) &&
        !MASTER_EXPRESSION_TARGETS.includes(b.block.target),
    );
    await masterApplier.applyBatch(applicable.map((b) => b.block));
    applicable.forEach((b) => markApplied(b.key));
  };

  const handleDestructiveConfirm = async () => {
    const { block } = destructiveState;
    setDestructiveState(INITIAL_DESTRUCTIVE_STATE);
    if (!block) return;
    await masterApplier.applyDestructive(block);
  };

  const handleReviewApplied = () => {
    if (reviewState) markApplied(reviewState.key);
    setReviewState(null);
  };

  const getValidationErrors = (
    messageId: string,
    actionOrdinal: number,
  ): string[] | undefined =>
    blockValidationByMessage[messageId]?.find((v) => v.index === actionOrdinal)
      ?.errors;

  const renderMessageSegments = (
    messageId: string,
    segments: MessageSegment[],
  ) => {
    let actionOrdinal = -1;
    const rendered = segments.map((segment, idx) => {
      if (segment.type === "text") {
        return (
          <span key={idx} className="whitespace-pre-wrap">
            {segment.content}
          </span>
        );
      }
      actionOrdinal += 1;
      const ordinal = actionOrdinal;
      const key = `${messageId}:${ordinal}`;
      if (scopedTab) {
        return (
          <ScopedProposalCard
            key={idx}
            proposal={scopedTab.describeProposal(segment.block)}
            state={scopedProposals.stateByKey[key] ?? "pending"}
            onAccept={(shownBefore) =>
              scopedProposals.accept(segment.block, key, shownBefore)
            }
            onDismiss={() => scopedProposals.dismiss(key)}
          />
        );
      }
      return (
        <ActionCard
          key={idx}
          block={segment.block}
          isApplied={appliedKeys.has(key)}
          validationErrors={getValidationErrors(messageId, ordinal)}
          onApply={(block) => handleApplyBlock(block, key)}
        />
      );
    });

    const actionEntries = segments
      .filter(
        (s): s is Extract<MessageSegment, { type: "action" }> =>
          s.type === "action",
      )
      .map((segment, ordinal) => ({
        block: segment.block,
        key: `${messageId}:${ordinal}`,
      }));
    const showApplyAll = !scopedTab && actionEntries.length > 1;

    return (
      <div>
        {rendered}
        {showApplyAll && (
          <button
            type="button"
            onClick={() => handleApplyAll(actionEntries)}
            className="rounded-md mt-1 px-3 py-1.5 text-xs font-semibold uppercase tracking-wider bg-accent/10 text-accent hover:bg-accent/20 border border-accent/40 transition-colors"
          >
            Apply All ({actionEntries.length})
          </button>
        )}
      </div>
    );
  };

  const handleClearChat = () => {
    if (!isConfirmingClear) {
      setIsConfirmingClear(true);
      return;
    }
    clearChat();
    setIsConfirmingClear(false);
  };

  return (
    <div className="flex flex-col h-full bg-surface-inset font-sans text-content-muted relative">
      {scopedTab ? (
        <ScopedChatHeader context={scopedTab.context} onNewChat={clearChat} />
      ) : (
        <div className="flex items-center justify-end gap-2 px-3 py-2 border-b border-border-subtle">
          {isConfirmingClear && (
            <button
              type="button"
              onClick={() => setIsConfirmingClear(false)}
              className="text-[10px] font-mono uppercase tracking-wider text-content-faint hover:text-content-muted"
            >
              Cancel
            </button>
          )}
          <button
            type="button"
            onClick={handleClearChat}
            className={`rounded-md px-2 py-1 text-[10px] font-mono uppercase tracking-wider transition-colors ${
              isConfirmingClear
                ? "bg-danger/10 text-danger border border-danger/40 hover:bg-danger/20"
                : "text-content-faint hover:text-content-muted"
            }`}
          >
            {isConfirmingClear ? "Confirm clear?" : "Clear chat"}
          </button>
        </div>
      )}

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex flex-col ${msg.role === "user" ? "items-end" : "items-start"}`}
          >
            <div
              className={`px-3 py-2 rounded-md max-w-[95%] font-sans text-sm leading-relaxed border ${
                msg.role === "user"
                  ? "bg-surface text-content border-border-subtle"
                  : "bg-surface-inset text-content border-border-subtle shadow-xs"
              }`}
            >
              {msg.role === "assistant" ? (
                <div>
                  {renderMessageSegments(
                    msg.id,
                    parseMessageSegments(msg.content),
                  )}
                  {msg.content === "" && isStreaming && (
                    <span className="inline-block animate-pulse text-content-faint font-mono text-xs">
                      Thinking...
                    </span>
                  )}
                </div>
              ) : (
                <span className="whitespace-pre-wrap">{msg.content}</span>
              )}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Dynamic Quick Prompt Chips */}
      {!scopedTab && (
        <QuickPromptChips
          activeSection={activeSection}
          onSelectPrompt={(p) => sendMessage(p)}
          disabled={isStreaming}
        />
      )}

      {/* Input Form */}
      <div className="p-3 border-t border-border-subtle bg-surface-inset">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
            placeholder={scopedTab ? "Ask about this tab..." : "Ask anything about your scenario..."}
            className="flex-1 bg-surface border border-border-subtle rounded-md px-3 py-2 text-sm font-sans text-content placeholder:text-content-faint focus:outline-hidden focus:border-border-strong"
          />
          {isStreaming ? (
            <button
              type="button"
              onClick={stopGeneration}
              className="rounded-md px-3 py-2 bg-danger/10 text-danger hover:bg-danger/20 border border-danger/40 text-xs font-mono uppercase tracking-wider transition-colors"
            >
              Stop
            </button>
          ) : (
            <button
              type="button"
              onClick={handleSend}
              disabled={!input.trim()}
              className="p-2 bg-content text-surface hover:bg-white rounded-md transition-colors border border-content disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <svg
                className="w-4 h-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                />
              </svg>
            </button>
          )}
        </div>
      </div>

      {scopedTab && (
        <ConflictModal
          state={scopedProposals.conflict}
          onReplace={() => scopedProposals.resolveConflict("replace")}
          onAppend={() => scopedProposals.resolveConflict("append")}
          onClose={scopedProposals.closeConflict}
        />
      )}

      {/* Destructive Action Confirmation Modal */}
      <DestructiveConfirmModal
        state={destructiveState}
        onConfirm={() => void handleDestructiveConfirm()}
        onClose={() => setDestructiveState(INITIAL_DESTRUCTIVE_STATE)}
      />

      {/* Expression-Tree Review Modal (conditions/invariants/end conditions) */}
      {scenarioId && (
        <ExpressionReviewModal
          target={reviewState?.target ?? null}
          scenarioId={scenarioId}
          draft={reviewState?.draft ?? null}
          onClose={() => setReviewState(null)}
          onApplied={handleReviewApplied}
        />
      )}
    </div>
  );
};
