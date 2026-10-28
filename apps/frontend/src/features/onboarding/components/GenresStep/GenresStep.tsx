import React from "react";
import { GENRES } from "@/shared/constants/genres";
import { MAX_PREFERRED_GENRES } from "../../constants/onboarding.constants";
import { useOnboardingStore } from "../../stores/onboarding.store";
import { GenreTile } from "../GenreTile/GenreTile";
import { StepFooter } from "../StepFooter/StepFooter";
import { StepHeading } from "../StepHeading/StepHeading";
import type { GenresStepProps } from "./GenresStep.types";

export const GenresStep: React.FC<GenresStepProps> = ({
  onNext,
  onBack,
  onSkip,
}) => {
  const genres = useOnboardingStore((state) => state.genres);
  const toggleGenre = useOnboardingStore((state) => state.toggleGenre);
  const isAtLimit = genres.length >= MAX_PREFERRED_GENRES;

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onNext();
  };

  return (
    <form aria-labelledby="onboarding-genres-title" onSubmit={handleSubmit}>
      <div className="mb-6">
        <span className="mb-1 block font-mono text-xs uppercase tracking-wider text-content-faint">
          Step 1 of 3
        </span>
        <StepHeading
          id="onboarding-genres-title"
          className="text-2xl md:text-3xl"
        >
          What do you like to read?
        </StepHeading>
        <div className="mt-1 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm text-content-muted">
            Pick up to 3 genres to personalize your recommendations.
          </p>
          <span className="inline-flex self-start rounded border border-border-subtle bg-surface-raised px-2 py-0.5 font-mono text-xs text-content sm:self-auto">
            {genres.length} of {MAX_PREFERRED_GENRES} selected
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {GENRES.map((genre) => (
          <GenreTile
            key={genre}
            genre={genre}
            isSelected={genres.includes(genre)}
            isDisabled={isAtLimit}
            onToggle={toggleGenre}
          />
        ))}
      </div>

      {isAtLimit && (
        <p role="status" className="mt-3 font-mono text-xs text-content-faint">
          Up to {MAX_PREFERRED_GENRES}
        </p>
      )}

      <StepFooter onBack={onBack} onSkip={onSkip} onNext={onNext} />
    </form>
  );
};
