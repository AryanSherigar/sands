import React, { useEffect, useState } from "react";
import type { ScopedProposal, ScopedProposalState } from "../../types/scopedChat.types";

export interface ScopedProposalCardProps {
  proposal: ScopedProposal;
  state: ScopedProposalState;
  onAccept: (shownBefore: string) => void;
  onDismiss: () => void;
}

const EMPTY_VALUE_LABEL = "Empty";

const ValueBlock: React.FC<{ title: string; text: string }> = ({ title, text }) => (
  <div className="space-y-1">
    <p className="text-micro text-content-faint">{title}</p>
    <p className="max-h-40 overflow-y-auto whitespace-pre-wrap rounded-md border border-border-subtle bg-surface-inset p-2 text-meta text-content">
      {text.trim() ? text : EMPTY_VALUE_LABEL}
    </p>
  </div>
);

export const ScopedProposalCard: React.FC<ScopedProposalCardProps> = ({
  proposal,
  state,
  onAccept,
  onDismiss,
}) => {
  const [baseline, setBaseline] = useState<string | null>(null);
  const { canApply, before } = proposal;

  useEffect(() => {
    if (canApply && baseline === null) setBaseline(before);
  }, [baseline, before, canApply]);

  if (state === "dismissed") {
    return <p className="my-2 text-micro text-content-faint">Dismissed: {proposal.label}</p>;
  }
  const shownBefore = baseline ?? before;
  const isApplied = state === "applied";

  return (
    <div className="my-3 space-y-2 rounded-md border border-border-subtle bg-surface p-3">
      <p className="text-meta font-medium text-content">Suggested change · {proposal.label}</p>
      <ValueBlock title="Before" text={shownBefore} />
      <ValueBlock title="After" text={proposal.after} />
      {proposal.reason && <p className="text-micro text-warning">{proposal.reason}</p>}
      <div className="flex items-center justify-end gap-2">
        {!isApplied && (
          <button
            type="button"
            onClick={onDismiss}
            className="rounded-md px-2.5 py-1 text-meta text-content-muted transition-colors hover:text-content"
          >
            Dismiss
          </button>
        )}
        <button
          type="button"
          disabled={isApplied || !canApply}
          onClick={() => onAccept(shownBefore)}
          className="rounded-md border border-content bg-content px-3 py-1 text-meta font-medium text-surface transition-colors disabled:cursor-not-allowed disabled:opacity-40"
        >
          {isApplied ? "Accepted" : "Accept"}
        </button>
      </div>
    </div>
  );
};
