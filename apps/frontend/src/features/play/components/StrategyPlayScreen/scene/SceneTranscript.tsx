import React from "react";
import type { SceneTranscriptProps } from "./SceneTranscript.types";

const PLAYER_BUBBLE = "self-end rounded-lg bg-primary/15 px-3 py-2 text-sm text-content";
const LEADER_BUBBLE =
  "self-start rounded-lg border border-border-subtle bg-surface-raised px-3 py-2 text-sm text-content";

export const SceneTranscript: React.FC<SceneTranscriptProps> = ({
  exchanges,
  leaderName,
  pendingPlayerText,
  streamingReply,
}) => {
  return (
    <ol
      aria-label="Conversation"
      aria-live="polite"
      className="flex max-h-[40vh] flex-col gap-2 overflow-y-auto py-2"
    >
      {exchanges.map((exchange) => (
        <React.Fragment key={exchange.sequence}>
          <li className={PLAYER_BUBBLE}>{exchange.player_text}</li>
          <li className={LEADER_BUBBLE}>
            <span className="mb-0.5 block text-micro font-semibold text-content-muted">
              {leaderName}
            </span>
            {exchange.leader_text}
          </li>
        </React.Fragment>
      ))}
      {pendingPlayerText ? <li className={PLAYER_BUBBLE}>{pendingPlayerText}</li> : null}
      {pendingPlayerText ? (
        <li className={LEADER_BUBBLE}>
          <span className="mb-0.5 block text-micro font-semibold text-content-muted">
            {leaderName}
          </span>
          {streamingReply || "…"}
        </li>
      ) : null}
    </ol>
  );
};
