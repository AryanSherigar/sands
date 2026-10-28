import React from "react";
import { ATMOSPHERIC_BANNER_PRESETS } from "../../constants/onboarding.constants";
import type { ProfilePreviewProps } from "./ProfilePreview.types";

export const ProfilePreview: React.FC<ProfilePreviewProps> = ({
  displayName,
  bio,
  avatarUrl,
  bannerUrl,
}) => {
  const effectiveBanner =
    bannerUrl || ATMOSPHERIC_BANNER_PRESETS[0].url;
  const initials = (displayName.trim() || "sands").slice(0, 2).toUpperCase();

  return (
    <div
      data-testid="profile-preview"
      className="rounded-xl border border-border-subtle bg-surface-raised p-4 shadow-xs"
    >
      <span className="mb-2.5 block font-mono text-[11px] uppercase tracking-wider text-content-faint">
        Live Header Preview
      </span>
      <div className="relative w-full overflow-hidden rounded-lg border border-border-subtle bg-surface-sunken">
        {/* Banner Preview */}
        <div
          className="h-28 w-full bg-cover bg-center transition-all duration-300"
          style={{ backgroundImage: `url('${effectiveBanner}')` }}
        >
          <div className="h-full w-full bg-linear-to-t from-surface-raised via-transparent to-black/30" />
        </div>

        {/* Profile Info Bar */}
        <div className="relative -mt-6 flex items-end gap-3 px-4 pb-3.5 pt-0">
          <div className="flex h-14 w-14 shrink-0 items-center justify-center overflow-hidden rounded-full border-2 border-surface-raised bg-surface-overlay font-display text-base font-semibold text-content shadow-md">
            {avatarUrl ? (
              <img
                src={avatarUrl}
                alt=""
                className="h-full w-full object-cover"
              />
            ) : (
              <span>{initials}</span>
            )}
          </div>
          <div className="min-w-0 flex-1 pb-0.5">
            <div className="flex items-center gap-2">
              <span className="truncate font-display text-sm font-semibold text-content">
                {displayName || "anonymous"}
              </span>
              <span className="rounded border border-border-subtle bg-surface px-1.5 py-0.5 font-mono text-[10px] text-content-faint">
                Reader
              </span>
            </div>
            {bio ? (
              <p className="mt-0.5 truncate text-xs text-content-muted">{bio}</p>
            ) : (
              <p className="mt-0.5 truncate text-xs text-content-faint italic">
                No bio yet.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
