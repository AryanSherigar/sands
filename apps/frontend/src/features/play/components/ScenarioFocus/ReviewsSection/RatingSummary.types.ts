import type { RatingBucket } from "../../../types/scenarioPage.types";

export interface RatingSummaryProps {
  average: number;
  reviewCount: number;
  buckets: RatingBucket[];
}
