import React from "react";
import { AVATAR_PRESETS } from "@/shared/constants/profile-presets";
import {
  ATMOSPHERIC_BANNER_PRESETS,
  MAX_BIO_LENGTH,
  MAX_DISPLAY_NAME_LENGTH,
} from "../../constants/onboarding.constants";
import { useOnboardingStore } from "../../stores/onboarding.store";
import { PresetPicker } from "../PresetPicker/PresetPicker";
import { ProfilePreview } from "../ProfilePreview/ProfilePreview";
import { StepFooter } from "../StepFooter/StepFooter";
import { StepHeading } from "../StepHeading/StepHeading";
import type { ProfileStepProps } from "./ProfileStep.types";

const INPUT_CLASSES =
  "w-full rounded-md border border-border-strong bg-surface-inset px-3.5 py-2.5 text-sm text-content transition-all focus:border-primary focus:outline-hidden focus:ring-2 focus:ring-white/10";

export const ProfileStep: React.FC<ProfileStepProps> = ({
  onNext,
  onBack,
  onSkip,
}) => {
  const displayName = useOnboardingStore((state) => state.displayName);
  const bio = useOnboardingStore((state) => state.bio);
  const avatarUrl = useOnboardingStore((state) => state.avatarUrl);
  const bannerUrl = useOnboardingStore((state) => state.bannerUrl);
  const setDisplayName = useOnboardingStore((state) => state.setDisplayName);
  const setBio = useOnboardingStore((state) => state.setBio);
  const setAvatarUrl = useOnboardingStore((state) => state.setAvatarUrl);
  const setBannerUrl = useOnboardingStore((state) => state.setBannerUrl);

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onNext();
  };

  const activeBanner = bannerUrl || ATMOSPHERIC_BANNER_PRESETS[0].url;

  return (
    <form aria-labelledby="onboarding-profile-title" onSubmit={handleSubmit}>
      <div className="mb-6">
        <span className="mb-1 block font-mono text-xs uppercase tracking-wider text-content-faint">
          Step 2 of 3
        </span>
        <StepHeading
          id="onboarding-profile-title"
          className="text-2xl md:text-3xl"
        >
          Who are you, adventurer?
        </StepHeading>
        <p className="mt-1 text-sm text-content-muted">
          This is how you appear to other players and in authored scenario recaps.
        </p>
      </div>

      <div className="space-y-5">
        <ProfilePreview
          displayName={displayName}
          bio={bio}
          avatarUrl={avatarUrl}
          bannerUrl={bannerUrl}
        />

        {/* Display Name */}
        <div>
          <label
            htmlFor="onboarding-display-name"
            className="mb-1.5 block text-xs font-medium text-content"
          >
            Display name{" "}
            <span className="font-mono text-content-faint">(required)</span>
          </label>
          <div className="relative">
            <input
              id="onboarding-display-name"
              type="text"
              maxLength={MAX_DISPLAY_NAME_LENGTH}
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
              className={INPUT_CLASSES}
              placeholder="e.g. Eldrin"
            />
            <span
              className="pointer-events-none absolute right-3 top-2.5 font-mono text-xs text-content-faint"
              aria-hidden="true"
            >
              @
            </span>
          </div>
        </div>

        {/* Short Bio */}
        <div>
          <div className="mb-1.5 flex items-center justify-between">
            <label
              htmlFor="onboarding-bio"
              className="block text-xs font-medium text-content"
            >
              Short bio{" "}
              <span className="font-mono text-content-faint">(optional)</span>
            </label>
            <span className="font-mono text-[11px] text-content-faint">
              {bio.length} / {MAX_BIO_LENGTH}
            </span>
          </div>
          <textarea
            id="onboarding-bio"
            rows={2}
            maxLength={MAX_BIO_LENGTH}
            value={bio}
            onChange={(event) => setBio(event.target.value)}
            className={`${INPUT_CLASSES} resize-none`}
            placeholder="Explorer of cold procedural noir & ancient obsidian archives."
          />
        </div>

        {/* Preset Banner Atmosphere */}
        <div>
          <label className="mb-2 block text-xs font-medium text-content">
            Preset Banner Atmosphere
          </label>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            {ATMOSPHERIC_BANNER_PRESETS.map((preset) => {
              const isSelected = activeBanner === preset.url;
              return (
                <button
                  key={preset.id}
                  type="button"
                  onClick={() => setBannerUrl(preset.url)}
                  aria-pressed={isSelected}
                  className={`relative h-12 overflow-hidden rounded-md border border-border-subtle bg-cover bg-center transition-all ${
                    isSelected
                      ? "ring-2 ring-content"
                      : "opacity-80 hover:opacity-100"
                  }`}
                  style={{ backgroundImage: `url('${preset.url}')` }}
                >
                  <span className="absolute inset-0 flex items-center justify-center bg-black/40 font-mono text-[10px] text-content">
                    {preset.name}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Avatar Presets */}
        <PresetPicker
          label="Avatar"
          options={AVATAR_PRESETS}
          selectedUrl={avatarUrl}
          onSelect={setAvatarUrl}
        />
      </div>

      <StepFooter onBack={onBack} onSkip={onSkip} onNext={onNext} />
    </form>
  );
};
