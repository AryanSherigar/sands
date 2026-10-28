import React from "react";
import { REVIEWS_SECTION_ID } from "../../../constants/scenarioPage.constants";
import { SectionError } from "../SectionError/SectionError";
import { SectionHeading } from "../SectionHeading";
import { ReviewsBody } from "./ReviewsBody";
import type { ReviewsSectionProps } from "./ReviewsSection.types";

export const ReviewsSection: React.FC<ReviewsSectionProps> = ({
  isError,
  onRetry,
  ...bodyProps
}) => (
  <section
    id={REVIEWS_SECTION_ID}
    aria-labelledby="scenario-reviews-heading"
    className="scroll-mt-20 space-y-4"
  >
    <SectionHeading id="scenario-reviews-heading" label="Reviews" />
    {isError && <SectionError label="reviews" onRetry={onRetry} />}
    {!isError && <ReviewsBody {...bodyProps} />}
  </section>
);
