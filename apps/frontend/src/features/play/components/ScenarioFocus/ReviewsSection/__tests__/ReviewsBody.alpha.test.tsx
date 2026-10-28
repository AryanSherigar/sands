import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ALPHA_CONFIG, NON_ALPHA_CONFIG } from "@/test/alphaFixtures";
import { createQueryWrapper } from "@/test/queryWrapper";
import type { AlphaConfig } from "@/shared/types/alpha.types";
import { ReviewsBody } from "../ReviewsBody";

const renderBody = (config: AlphaConfig): void => {
  const Wrapper = createQueryWrapper(config);
  render(
    <Wrapper>
      <ReviewsBody
        reviews={[]}
        ownReview={null}
        totalReviews={0}
        averageRating={0}
        ratingCounts={[]}
        hasMoreReviews={false}
        isLoadingMoreReviews={false}
        canReview
        isSignedIn
        isSubmittingReview={false}
        onLoadMore={vi.fn()}
        onRequestSignIn={vi.fn()}
        onSubmitReview={vi.fn()}
      />
    </Wrapper>,
  );
};

describe("ReviewsBody review form", () => {
  it("lets an eligible player post a review when alpha mode is off", () => {
    renderBody(NON_ALPHA_CONFIG);
    expect(screen.getByRole("button", { name: "Post review" })).toBeInTheDocument();
  });

  it("shows neither the form nor an eligibility prompt in alpha mode", () => {
    renderBody(ALPHA_CONFIG);
    expect(screen.queryByRole("button", { name: "Post review" })).toBeNull();
    expect(screen.getByText("No reviews yet")).toBeInTheDocument();
  });
});
