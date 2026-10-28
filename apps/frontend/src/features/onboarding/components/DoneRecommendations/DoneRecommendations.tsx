import React from "react";
import { Link } from "react-router-dom";
import { motion, useReducedMotion } from "motion/react";
import { MOTION_CARD_STAGGER_SECONDS } from "@/shared/constants/motion";
import {
  buildRevealContainerVariants,
  buildRevealItemVariants,
} from "@/shared/lib/motion-variants";
import {
  RECOMMENDATION_SKELETON_COUNT,
  SHOWCASE_RECOMMENDATIONS,
} from "../../constants/onboarding.constants";
import type { DoneRecommendationsProps } from "./DoneRecommendations.types";

const SKELETON_SLOTS = Array.from(
  { length: RECOMMENDATION_SKELETON_COUNT },
  (_, index) => index,
);

export const DoneRecommendations: React.FC<DoneRecommendationsProps> = ({
  isLoading,
  items,
}) => {
  const shouldReduceMotion = useReducedMotion() ?? false;

  if (isLoading) {
    return (
      <div
        aria-busy="true"
        className="mt-8 grid grid-cols-1 gap-3.5 sm:grid-cols-3"
      >
        {SKELETON_SLOTS.map((slot) => (
          <div
            key={slot}
            className="aspect-3/4 animate-pulse rounded-xl border border-border-subtle bg-surface-raised"
          />
        ))}
      </div>
    );
  }

  // If custom items are passed, render them
  if (items.length > 0) {
    return (
      <motion.ul
        aria-label="Recommended stories"
        variants={buildRevealContainerVariants(
          shouldReduceMotion,
          MOTION_CARD_STAGGER_SECONDS,
        )}
        initial="hidden"
        animate="show"
        className="mt-8 grid grid-cols-1 gap-3.5 sm:grid-cols-3"
      >
        {items.map((item, index) => (
          <motion.li
            key={index}
            variants={buildRevealItemVariants(shouldReduceMotion)}
          >
            {item}
          </motion.li>
        ))}
      </motion.ul>
    );
  }

  // Fallback to curated Quiet Cinematic 3:4 showcase cards
  return (
    <motion.div
      aria-label="Recommended stories"
      variants={buildRevealContainerVariants(
        shouldReduceMotion,
        MOTION_CARD_STAGGER_SECONDS,
      )}
      initial="hidden"
      animate="show"
      className="mt-8 grid grid-cols-1 gap-3.5 text-left sm:grid-cols-3"
    >
      {SHOWCASE_RECOMMENDATIONS.map((scenario) => (
        <motion.div
          key={scenario.id}
          variants={buildRevealItemVariants(shouldReduceMotion)}
          className="group flex flex-col justify-between overflow-hidden rounded-xl border border-border-subtle bg-surface-raised p-3 shadow-xs transition-all hover:border-border-strong"
        >
          <div className="relative mb-3 aspect-3/4 w-full overflow-hidden rounded-lg bg-surface-sunken">
            <img
              src={scenario.imageUrl}
              alt={scenario.title}
              className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
            />
            <div className="absolute inset-0 bg-linear-to-t from-surface-raised via-transparent to-transparent opacity-80" />
            <span
              className="absolute left-2.5 top-2.5 rounded border border-border-subtle bg-surface/85 px-2 py-0.5 font-mono text-[10px] font-medium backdrop-blur-sm"
              style={{ color: scenario.genreColor }}
            >
              {scenario.genre}
            </span>
          </div>

          <div>
            <h3 className="font-display text-sm font-semibold text-content transition-colors group-hover:text-primary">
              {scenario.title}
            </h3>
            <p className="mt-1 line-clamp-2 text-xs text-content-faint">
              {scenario.description}
            </p>
            <div className="mt-3 flex items-center justify-between border-t border-border-subtle pt-2.5 font-mono text-[11px] text-content-faint">
              <span>
                ★ {scenario.rating} · {scenario.plays} plays
              </span>
              <Link
                to={`/play?scenario=${scenario.id}`}
                className="font-medium text-content transition-colors hover:text-white"
              >
                Play →
              </Link>
            </div>
          </div>
        </motion.div>
      ))}
    </motion.div>
  );
};
