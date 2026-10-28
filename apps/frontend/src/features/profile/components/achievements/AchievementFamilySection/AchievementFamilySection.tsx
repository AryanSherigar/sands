import React from "react";
import { AchievementBadge } from "../AchievementBadge/AchievementBadge";
import type { AchievementFamilySectionProps } from "./AchievementFamilySection.types";

export const AchievementFamilySection: React.FC<
  AchievementFamilySectionProps
> = ({ family, items }) => (
  <section aria-labelledby={`achievements-${family}`} className="space-y-3">
    <h2
      id={`achievements-${family}`}
      className="font-display text-lg font-semibold text-content"
    >
      {family}
    </h2>
    <ul className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
      {items.map((item) => (
        <AchievementBadge key={item.key} item={item} />
      ))}
    </ul>
  </section>
);
