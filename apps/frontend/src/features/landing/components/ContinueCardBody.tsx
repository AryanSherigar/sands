import React from "react";
import { IconClock, IconPlayerPlayFilled } from "@tabler/icons-react";
import { formatRelativeTime } from "../utils/formatRelativeTime";
import type { ContinueCardBodyProps } from "./ContinueCardBody.types";

export const ContinueCardBody: React.FC<ContinueCardBodyProps> = ({
  title,
  turnCount,
  author,
  excerpt,
  updatedAt,
}) => (
  <div className="flex flex-1 flex-col justify-between gap-3 p-5">
    <div>
      <div className="mb-1 flex items-center justify-between gap-2">
        <h3 className="font-display text-base font-semibold text-content transition-colors group-hover:text-primary">
          {title}
        </h3>
        <span className="rounded-sm bg-surface-inset px-2 py-0.5 font-mono text-xs font-medium text-accent">
          Turn {turnCount}
        </span>
      </div>
      <p className="mb-2 font-sans text-xs text-content-faint">{author}</p>
      <p className="line-clamp-2 font-sans text-sm italic leading-relaxed text-content-muted">
        “{excerpt}”
      </p>
    </div>
    <div className="flex items-center justify-between border-t border-border-subtle pt-3">
      <span className="inline-flex items-center gap-1 font-mono text-xs text-content-faint">
        <IconClock size={14} stroke={1.5} />
        Played {formatRelativeTime(updatedAt)}
      </span>
      <span className="inline-flex items-center justify-center gap-1.5 rounded-md border border-border-strong bg-surface px-4 py-1.5 font-sans text-xs font-medium text-content transition-colors group-hover:bg-surface-overlay group-hover:text-primary">
        <IconPlayerPlayFilled size={12} stroke={1.5} />
        Continue
      </span>
    </div>
  </div>
);
