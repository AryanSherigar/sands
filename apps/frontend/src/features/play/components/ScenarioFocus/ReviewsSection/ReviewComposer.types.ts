import type { ScenarioReviewResponse } from "../../../types/scenario";

export interface ReviewComposerProps {
  existingReview: ScenarioReviewResponse | undefined;
  isSubmitting: boolean;
  onSubmit: (data: { rating: number; comment?: string }) => Promise<unknown>;
}
