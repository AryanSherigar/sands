import React from "react";
import { Link } from "react-router-dom";
import { formatRelativeTime } from "@/shared/lib/formatRelativeTime";
import { CreatorAvatar } from "../CreatorAvatar/CreatorAvatar";
import type { HeroCreatorRowProps } from "./HeroCreatorRow.types";

const ANONYMOUS_CREATOR_LABEL = "Anonymous";

export const HeroCreatorRow: React.FC<HeroCreatorRowProps> = ({
  creatorId,
  creatorDisplayName,
  creatorAvatarUrl,
  updatedAt,
}) => (
  <div className="flex flex-wrap items-center gap-x-3 gap-y-1 font-sans text-sm">
    <Link
      to={`/profile/${creatorId}`}
      className="group flex items-center gap-2 text-content"
    >
      <CreatorAvatar
        displayName={creatorDisplayName}
        avatarUrl={creatorAvatarUrl}
        sizeClassName="h-7 w-7"
      />
      <span className="font-semibold group-hover:underline">
        {creatorDisplayName ?? ANONYMOUS_CREATOR_LABEL}
      </span>
    </Link>
    <span aria-hidden="true" className="text-content-faint">
      ·
    </span>
    <span className="text-xs text-content-faint">
      Updated {formatRelativeTime(updatedAt, new Date())}
    </span>
  </div>
);
