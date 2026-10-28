import React from "react";
import { Link } from "react-router-dom";
import { IconArrowRight, IconCheck } from "@tabler/icons-react";
import { motion, useReducedMotion } from "motion/react";
import { buildRevealItemVariants } from "@/shared/lib/motion-variants";
import { DoneRecommendations } from "../DoneRecommendations/DoneRecommendations";
import { StepHeading } from "../StepHeading/StepHeading";
import type { DoneStepProps } from "./DoneStep.types";

const PRIMARY_LINK_CLASSES =
  "inline-flex w-full items-center justify-center gap-2 whitespace-nowrap rounded-md bg-primary px-6 py-2.5 text-sm font-semibold text-primary-contrast transition-opacity hover:opacity-95 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-content active:scale-[0.98]";

const SECONDARY_LINK_CLASSES =
  "inline-flex w-full items-center justify-center whitespace-nowrap rounded-md border border-border-strong bg-surface-raised px-6 py-2.5 text-sm font-medium text-content transition-colors hover:bg-white/6 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-content active:scale-[0.98]";

export const DoneStep: React.FC<DoneStepProps> = ({ genres, exploreHref }) => {
  const shouldReduceMotion = useReducedMotion() ?? false;

  return (
    <section aria-labelledby="onboarding-done-title" className="text-center">
      {/* Staged Arrival Header */}
      <div className="mb-6 flex flex-col items-center">
        <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-full border border-border-subtle bg-surface-raised shadow-xs">
          <IconCheck size={22} className="text-success" aria-hidden="true" />
        </div>
        <StepHeading id="onboarding-done-title" className="text-3xl md:text-4xl">
          You&apos;re all set
        </StepHeading>
        {genres.length > 0 ? (
          <p className="mx-auto mt-2 max-w-md text-sm text-content-muted">
            Based on your taste in{" "}
            <span className="font-medium text-content">{genres.join(", ")}</span>
            , here are stories ready to begin immediately.
          </p>
        ) : (
          <p className="mx-auto mt-2 max-w-md text-sm text-content-muted">
            Here are stories ready to begin immediately.
          </p>
        )}
      </div>

      <DoneRecommendations isLoading={false} items={[]} />

      <motion.div
        variants={buildRevealItemVariants(shouldReduceMotion)}
        initial="hidden"
        animate="show"
        className="mx-auto mt-8 flex w-full max-w-sm flex-col items-center justify-center gap-3 sm:flex-row"
      >
        <Link
          to={exploreHref}
          className={PRIMARY_LINK_CLASSES}
          aria-label="Explore stories"
        >
          <span>Explore stories</span>
          <IconArrowRight size={16} aria-hidden="true" />
        </Link>
        <Link to="/" className={SECONDARY_LINK_CLASSES}>
          Go home
        </Link>
      </motion.div>
    </section>
  );
};
