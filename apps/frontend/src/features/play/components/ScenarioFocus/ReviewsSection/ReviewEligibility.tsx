import React from "react";
import { IconLock } from "@tabler/icons-react";
import { Button } from "@/shared/components/ui/Button";
import { MIN_TURNS_TO_REVIEW } from "../../../constants/scenarioPage.constants";
import type { ReviewEligibilityProps } from "./ReviewEligibility.types";

export const ReviewEligibility: React.FC<ReviewEligibilityProps> = ({
  isSignedIn,
  onRequestSignIn,
}) => {
  if (!isSignedIn) {
    return (
      <Button
        type="button"
        variant="secondary"
        size="md"
        onClick={onRequestSignIn}
      >
        Write a review
      </Button>
    );
  }

  return (
    <p className="flex items-center gap-2 font-sans text-sm text-content-faint">
      <IconLock size={15} stroke={1.5} aria-hidden="true" />
      Play at least {MIN_TURNS_TO_REVIEW} turns to review
    </p>
  );
};
