import React from "react";
import { Link } from "react-router-dom";
import { IconArrowRight } from "@tabler/icons-react";
import { CreatorAvatar } from "../CreatorAvatar/CreatorAvatar";
import type { AuthorDossierProps } from "./AuthorDossier.types";

const ANONYMOUS_CREATOR_LABEL = "Anonymous";

const formatOtherScenariosLabel = (count: number, name: string): string =>
  `View ${count} other ${count === 1 ? "scenario" : "scenarios"} by ${name}`;

export const AuthorDossier: React.FC<AuthorDossierProps> = ({
  creatorId,
  displayName,
  avatarUrl,
  bio,
  otherScenariosCount,
}) => {
  const name = displayName ?? ANONYMOUS_CREATOR_LABEL;
  const profilePath = `/profile/${creatorId}`;

  return (
    <section
      aria-label="About the author"
      className="space-y-3 rounded-md border border-border-subtle bg-surface-raised p-5"
    >
      <Link to={profilePath} className="flex items-center gap-3">
        <CreatorAvatar
          displayName={displayName}
          avatarUrl={avatarUrl}
          sizeClassName="h-11 w-11"
        />
        <span className="font-display text-sm font-bold text-content hover:underline">
          {name}
        </span>
      </Link>
      {bio && (
        <p className="font-sans text-xs leading-relaxed text-content-muted">
          {bio}
        </p>
      )}
      {otherScenariosCount > 0 && (
        <Link
          to={profilePath}
          className="group flex items-center justify-between gap-2 border-t border-border-subtle pt-3 font-sans text-xs font-medium text-accent hover:underline"
        >
          {formatOtherScenariosLabel(otherScenariosCount, name)}
          <IconArrowRight
            size={16}
            stroke={1.5}
            aria-hidden="true"
            className="transition-transform group-hover:translate-x-1"
          />
        </Link>
      )}
    </section>
  );
};
