import React, { useState } from "react";
import { IconStar, IconStarFilled } from "@tabler/icons-react";
import { Button } from "@/shared/components/ui/Button";
import { extractErrorMessage } from "@/shared/lib/extractErrorMessage";
import type { ReviewComposerProps } from "./ReviewComposer.types";

const STAR_VALUES = [1, 2, 3, 4, 5];
const DEFAULT_RATING = 5;
const SUBMIT_FAILED_MESSAGE = "Couldn't post your review.";

const getSubmitLabel = (isSubmitting: boolean, isEditing: boolean): string => {
  if (isSubmitting) return "Saving…";
  return isEditing ? "Update review" : "Post review";
};

export const ReviewComposer: React.FC<ReviewComposerProps> = ({
  existingReview,
  isSubmitting,
  onSubmit,
}) => {
  const [rating, setRating] = useState(existingReview?.rating ?? DEFAULT_RATING);
  const [comment, setComment] = useState(existingReview?.comment ?? "");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isPosted, setIsPosted] = useState(false);

  const handleSubmit = async (event: React.FormEvent): Promise<void> => {
    event.preventDefault();
    setErrorMessage(null);
    try {
      await onSubmit({ rating, comment: comment.trim() || undefined });
      setIsPosted(true);
    } catch (error: unknown) {
      setErrorMessage(extractErrorMessage(error, SUBMIT_FAILED_MESSAGE));
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-md border border-border-subtle bg-surface p-4"
    >
      <fieldset className="flex items-center justify-between">
        <legend className="font-sans text-sm text-content-muted">
          {existingReview ? "Your review" : "Rate this story"}
        </legend>
        <div className="flex items-center gap-1">
          {STAR_VALUES.map((star) => (
            <button
              key={star}
              type="button"
              onClick={() => setRating(star)}
              aria-label={`${star} ${star === 1 ? "star" : "stars"}`}
              aria-pressed={star === rating}
              className="text-accent transition-transform hover:scale-110 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent"
            >
              {star <= rating ? (
                <IconStarFilled size={20} />
              ) : (
                <IconStar size={20} stroke={1.5} className="text-content-faint" />
              )}
            </button>
          ))}
        </div>
      </fieldset>
      <label className="sr-only" htmlFor="scenario-review-comment">
        Review comment
      </label>
      <textarea
        id="scenario-review-comment"
        value={comment}
        onChange={(event) => setComment(event.target.value)}
        placeholder="What worked, what didn't — the narrative, the choices, the pacing."
        rows={3}
        className="mt-3 w-full resize-none rounded-sm border border-border-strong bg-surface-inset p-3 font-sans text-sm text-content placeholder:text-content-faint focus:border-primary focus:outline-hidden focus:ring-2 focus:ring-primary/20"
      />
      {errorMessage && (
        <p role="alert" className="mt-2 font-sans text-xs text-danger">
          {errorMessage}
        </p>
      )}
      {isPosted && !errorMessage && (
        <p role="status" className="mt-2 font-sans text-xs text-success">
          Review saved.
        </p>
      )}
      <div className="mt-3 flex justify-end">
        <Button
          type="submit"
          variant="secondary"
          size="sm"
          disabled={isSubmitting}
        >
          {getSubmitLabel(isSubmitting, Boolean(existingReview))}
        </Button>
      </div>
    </form>
  );
};
