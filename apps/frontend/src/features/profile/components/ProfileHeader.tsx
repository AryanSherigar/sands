import React from "react";
import { IconPencil } from "@tabler/icons-react";
import { Button } from "@/shared/components/ui/Button";
import {
  DEFAULT_AVATAR,
  DEFAULT_BANNER,
} from "@/shared/constants/profile-presets";
import { ProfileBio } from "./ProfileBio";
import type { ProfileHeaderProps } from "./ProfileHeader.types";

const formatJoinedDate = (createdAt: string): string =>
  new Date(createdAt).toLocaleDateString(undefined, {
    month: "short",
    year: "numeric",
  });

export const ProfileHeader: React.FC<ProfileHeaderProps> = ({
  profile,
  isOwner,
  onEditClick,
}) => (
  <header className="space-y-6">
    <div className="relative">
      <div className="aspect-4/1 max-h-60 w-full overflow-hidden rounded-md border border-border-subtle bg-surface-inset">
        <img
          src={profile.banner_url || DEFAULT_BANNER}
          alt={`${profile.display_name}'s banner`}
          className="h-full w-full object-cover"
        />
      </div>
      <div className="-mt-10 flex items-end justify-between gap-4 px-4 md:-mt-12 md:px-6">
        <img
          src={profile.avatar_url || DEFAULT_AVATAR}
          alt={profile.display_name}
          className="h-20 w-20 rounded-full border-4 border-surface bg-surface-raised object-cover md:h-28 md:w-28"
        />
        {isOwner && (
          <Button variant="secondary" onClick={onEditClick} className="mb-2">
            <IconPencil size={16} stroke={1.5} aria-hidden="true" />
            Edit profile
          </Button>
        )}
      </div>
    </div>
    <div className="space-y-2 px-1">
      <h1 className="wrap-break-word font-display text-3xl font-semibold tracking-tight text-content">
        {profile.display_name}
      </h1>
      <p className="text-xs text-content-faint">
        Joined {formatJoinedDate(profile.created_at)}
      </p>
      <ProfileBio bio={profile.bio} />
    </div>
  </header>
);
