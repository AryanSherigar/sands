import React from "react";
import { getCreatorInitials } from "../../../utils/scenarioPage.utils";
import type { CreatorAvatarProps } from "./CreatorAvatar.types";

export const CreatorAvatar: React.FC<CreatorAvatarProps> = ({
  displayName,
  avatarUrl,
  sizeClassName,
}) => {
  const frameClasses = `${sizeClassName} shrink-0 overflow-hidden rounded-full border border-border-strong bg-surface-inset`;

  if (avatarUrl) {
    return (
      <img
        src={avatarUrl}
        alt=""
        aria-hidden="true"
        className={`${frameClasses} object-cover`}
      />
    );
  }

  return (
    <span
      aria-hidden="true"
      className={`${frameClasses} flex items-center justify-center font-mono text-[11px] font-bold text-content`}
    >
      {getCreatorInitials(displayName)}
    </span>
  );
};
