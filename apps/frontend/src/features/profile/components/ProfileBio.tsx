import React, { useState } from "react";
import {
  BIO_COLLAPSE_CHAR_THRESHOLD,
  BIO_COLLAPSE_LINE_THRESHOLD,
} from "../constants/profileHeader.constants";
import type { ProfileBioProps } from "./ProfileBio.types";

const isLongBio = (bio: string): boolean =>
  bio.length > BIO_COLLAPSE_CHAR_THRESHOLD ||
  bio.split("\n").length > BIO_COLLAPSE_LINE_THRESHOLD;

export const ProfileBio: React.FC<ProfileBioProps> = ({ bio }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!bio) {
    return <p className="text-sm text-content-faint">No bio yet.</p>;
  }

  const clampClass = isExpanded ? "" : "line-clamp-3";

  return (
    <div className="max-w-2xl">
      <p
        className={`whitespace-pre-line wrap-break-word text-[0.9375rem] text-content-muted ${clampClass}`}
      >
        {bio}
      </p>
      {isLongBio(bio) && (
        <button
          type="button"
          aria-expanded={isExpanded}
          onClick={() => setIsExpanded((current) => !current)}
          className="mt-1 text-xs font-medium text-content hover:underline focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent"
        >
          {isExpanded ? "Less" : "More"}
        </button>
      )}
    </div>
  );
};
