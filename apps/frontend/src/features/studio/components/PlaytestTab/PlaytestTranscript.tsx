import React from "react";
import { PLAYTEST_PROLOGUE_HEADING } from "../../constants/playtest";
import type { PlaytestTranscriptProps } from "./PlaytestTab.types";

export const PlaytestTranscript: React.FC<PlaytestTranscriptProps> = ({
  openingText,
  turns,
  streamingNarration,
  isStreaming,
}) => (
  <div aria-live="polite" className="mx-auto w-full max-w-[68ch] space-y-6 px-4 py-6">
    <article className="rounded-lg border border-border-subtle bg-surface-raised p-4">
      <h3 className="mb-2 text-micro font-semibold uppercase tracking-wide text-content-faint">
        {PLAYTEST_PROLOGUE_HEADING}
      </h3>
      <p className="whitespace-pre-line text-body italic text-content">{openingText}</p>
    </article>
    {turns.map((turn) => (
      <article key={turn.id} className="space-y-2">
        <p className="text-meta font-medium text-content-muted">{turn.actionText}</p>
        <p className="whitespace-pre-line text-body text-content">{turn.narration}</p>
      </article>
    ))}
    {isStreaming && (
      <p className="whitespace-pre-line text-body text-content">
        {streamingNarration || "The narrator is thinking…"}
      </p>
    )}
  </div>
);
