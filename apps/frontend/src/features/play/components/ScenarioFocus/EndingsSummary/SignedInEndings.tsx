import React from "react";
import { getEndingsProgressPercent } from "../../../utils/scenarioPage.utils";
import { SectionHeading } from "../SectionHeading";
import { FoundEndingCard } from "./FoundEndingCard";
import { LockedEndingSlot } from "./LockedEndingSlot";
import type { SignedInEndingsProps } from "./SignedInEndings.types";

const PROGRESS_CLASSES =
  "h-1.5 w-full appearance-none overflow-hidden rounded-full [&::-moz-progress-bar]:bg-accent [&::-webkit-progress-bar]:bg-surface-raised [&::-webkit-progress-value]:bg-accent";

export const SignedInEndings: React.FC<SignedInEndingsProps> = ({
  totalCount,
  found,
}) => {
  const percent = getEndingsProgressPercent(found.length, totalCount);
  const lockedCount = Math.max(totalCount - found.length, 0);

  return (
    <section aria-labelledby="scenario-endings-heading" className="space-y-3">
      <SectionHeading
        id="scenario-endings-heading"
        label={`Endings found (${found.length} of ${totalCount})`}
        trailing={
          <span className="font-mono text-xs text-accent">
            {percent}% complete
          </span>
        }
      />
      <progress
        value={percent}
        max={100}
        aria-label="Endings found"
        className={PROGRESS_CLASSES}
      />
      <ul className="grid grid-cols-1 gap-3 md:grid-cols-2">
        {found.map((ending) => (
          <FoundEndingCard
            key={ending.ending_id ?? ending.title}
            ending={ending}
          />
        ))}
        {Array.from({ length: lockedCount }, (_, index) => (
          <LockedEndingSlot key={index} position={found.length + index + 1} />
        ))}
      </ul>
    </section>
  );
};
