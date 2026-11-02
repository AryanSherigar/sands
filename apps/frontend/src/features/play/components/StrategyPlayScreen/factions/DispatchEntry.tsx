import React from "react";
import type { DispatchEntryProps } from "./DispatchEntry.types";
import { buildFallbackNote, formatTraits } from "./dispatchText";

const READ_BUTTON_CLASS =
  "min-h-8 rounded-sm border border-border-strong px-2 text-meta font-semibold text-content transition-colors hover:bg-hover-wash focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary disabled:cursor-not-allowed disabled:opacity-40";

export const DispatchEntry: React.FC<DispatchEntryProps> = ({
  dispatch,
  streamedText,
  isStreaming,
  isDegraded,
  onRead,
}) => {
  const handleRead = () => onRead(dispatch);
  const isCompleted = dispatch.status === "completed";
  const shouldShowFallback = !isCompleted && !isStreaming && (isDegraded || dispatch.status === "failed");
  const bodyText = isCompleted ? dispatch.narration : streamedText;

  return (
    <article className="rounded-md border border-border-subtle bg-surface-raised p-3">
      <div className="flex items-center justify-between gap-2 text-meta text-content-muted">
        <span>
          {dispatch.agent.name} ({formatTraits(dispatch)})
        </span>
        <span>Turn {dispatch.turn + 1}</span>
      </div>
      {bodyText ? (
        <p className="mt-2 whitespace-pre-wrap text-body text-content" aria-live="polite">
          {bodyText}
        </p>
      ) : null}
      {shouldShowFallback ? (
        <p className="mt-2 text-body text-content-muted">{buildFallbackNote(dispatch)}</p>
      ) : null}
      {!bodyText && !shouldShowFallback ? (
        <p className="mt-2 text-body text-content-muted">
          {isStreaming ? "The dispatch is being written…" : "A sealed dispatch has arrived."}
        </p>
      ) : null}
      {isCompleted ? null : (
        <div className="mt-3">
          <button type="button" onClick={handleRead} disabled={isStreaming} className={READ_BUTTON_CLASS}>
            {isStreaming ? "Writing…" : "Read dispatch"}
          </button>
        </div>
      )}
    </article>
  );
};
