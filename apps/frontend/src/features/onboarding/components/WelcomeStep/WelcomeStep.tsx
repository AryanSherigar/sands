import React from "react";
import { IconArrowRight } from "@tabler/icons-react";
import { motion, useReducedMotion } from "motion/react";
import { useSkippableReveal } from "@/shared/hooks/useSkippableReveal";
import {
  buildRevealContainerVariants,
  buildRevealItemVariants,
} from "@/shared/lib/motion-variants";
import { StepHeading } from "../StepHeading/StepHeading";
import type { WelcomeStepProps } from "./WelcomeStep.types";

export const WelcomeStep: React.FC<WelcomeStepProps> = ({ onStart }) => {
  const shouldReduceMotion = useReducedMotion() ?? false;
  const { isSkipped } = useSkippableReveal();
  const containerVariants = buildRevealContainerVariants(shouldReduceMotion);
  const itemVariants = buildRevealItemVariants(shouldReduceMotion);

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onStart();
  };

  return (
    <form
      aria-labelledby="onboarding-welcome-title"
      onSubmit={handleSubmit}
      className="flex flex-col items-center py-4 text-center"
    >
      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate={isSkipped ? "skipped" : "show"}
        className="flex w-full flex-col items-center"
      >
        {/* Evocative glyph symbol */}
        <motion.div
          variants={itemVariants}
          className="mb-8 flex h-16 w-16 items-center justify-center rounded-2xl border border-border-subtle bg-surface-raised shadow-xs"
        >
          <svg
            className="h-8 w-8 text-content"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            aria-hidden="true"
          >
            <path
              d="M12 3v18M3 12h18M5.5 5.5l13 13M18.5 5.5l-13 13"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </motion.div>

        {/* Headings */}
        <motion.div variants={itemVariants} className="mb-8 max-w-lg space-y-3">
          <StepHeading
            id="onboarding-welcome-title"
            className="text-4xl leading-tight md:text-5xl"
          >
            Welcome to sands
          </StepHeading>
          <p className="mx-auto max-w-md text-base leading-relaxed text-content-muted">
            A place to play and create text stories narrated by an AI that
            remembers your choices and obeys the world’s rules.
          </p>
        </motion.div>

        {/* 3 Quiet Value Props */}
        <motion.div
          variants={itemVariants}
          className="mb-8 grid w-full max-w-md grid-cols-1 gap-3 text-left sm:grid-cols-3"
        >
          <div className="rounded-lg border border-border-subtle bg-surface-raised/70 p-3.5">
            <span className="mb-1 block text-xs font-semibold text-content">
              Persistent
            </span>
            <span className="text-[11px] leading-snug text-content-faint">
              Graph memory preserves every decision.
            </span>
          </div>
          <div className="rounded-lg border border-border-subtle bg-surface-raised/70 p-3.5">
            <span className="mb-1 block text-xs font-semibold text-content">
              Deterministic
            </span>
            <span className="text-[11px] leading-snug text-content-faint">
              Rules, dice, and state the narrator obeys.
            </span>
          </div>
          <div className="rounded-lg border border-border-subtle bg-surface-raised/70 p-3.5">
            <span className="mb-1 block text-xs font-semibold text-content">
              Your Rhythm
            </span>
            <span className="text-[11px] leading-snug text-content-faint">
              Take your time; stories wait quietly.
            </span>
          </div>
        </motion.div>

        {/* Primary CTA and helper copy */}
        <motion.div
          variants={itemVariants}
          className="flex w-full flex-col items-center"
        >
          <button
            type="submit"
            className="inline-flex min-w-[200px] items-center justify-center gap-2 whitespace-nowrap rounded-md bg-primary px-8 py-3 text-sm font-semibold text-primary-contrast transition-opacity hover:opacity-95 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-content active:scale-[0.98]"
          >
            <span>Get started</span>
            <IconArrowRight size={16} aria-hidden="true" />
          </button>
          <p className="mt-4 font-mono text-[11px] text-content-faint">
            Takes less than 1 minute · Fully skippable
          </p>
        </motion.div>
      </motion.div>
    </form>
  );
};
