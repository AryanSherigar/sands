import type { Variants } from "motion/react";
import {
  MOTION_DURATION_FAST_SECONDS,
  MOTION_DURATION_REVEAL_SECONDS,
  MOTION_DURATION_STEP_EXIT_SECONDS,
  MOTION_DURATION_STEP_SECONDS,
  MOTION_EASE_ENTER,
  MOTION_EASE_EXIT,
  MOTION_REVEAL_STAGGER_SECONDS,
  MOTION_STEP_TRAVEL_PIXELS,
} from "@/shared/constants/motion";

export function buildStepVariants(shouldReduceMotion: boolean): Variants {
  const travel = shouldReduceMotion ? 0 : MOTION_STEP_TRAVEL_PIXELS;
  const enterDuration = shouldReduceMotion
    ? MOTION_DURATION_FAST_SECONDS
    : MOTION_DURATION_STEP_SECONDS;
  const exitDuration = shouldReduceMotion
    ? MOTION_DURATION_FAST_SECONDS
    : MOTION_DURATION_STEP_EXIT_SECONDS;
  return {
    initial: { opacity: 0, y: travel },
    animate: {
      opacity: 1,
      y: 0,
      transition: { duration: enterDuration, ease: MOTION_EASE_ENTER },
    },
    exit: {
      opacity: 0,
      y: -travel,
      transition: { duration: exitDuration, ease: MOTION_EASE_EXIT },
    },
  };
}

export function buildRevealContainerVariants(
  shouldReduceMotion: boolean,
  stagger: number = MOTION_REVEAL_STAGGER_SECONDS,
): Variants {
  return {
    hidden: {},
    skipped: {},
    show: {
      transition: { staggerChildren: shouldReduceMotion ? 0 : stagger },
    },
  };
}

export function buildRevealItemVariants(shouldReduceMotion: boolean): Variants {
  return {
    hidden: {
      opacity: 0,
      y: shouldReduceMotion ? 0 : MOTION_STEP_TRAVEL_PIXELS,
    },
    skipped: { opacity: 1, y: 0, transition: { duration: 0 } },
    show: {
      opacity: 1,
      y: 0,
      transition: {
        duration: shouldReduceMotion
          ? MOTION_DURATION_FAST_SECONDS
          : MOTION_DURATION_REVEAL_SECONDS,
        ease: MOTION_EASE_ENTER,
      },
    },
  };
}

