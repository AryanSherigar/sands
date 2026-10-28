import React from "react";
import { IconClock, IconStarFilled, IconHistory } from "@tabler/icons-react";
import type { HeroMetaProps } from "./HeroMeta.types";

export const HeroMeta: React.FC<HeroMetaProps> = ({
  estimatedPlaytime,
  ratingAvg,
  playCount,
}) => {
  const rating = Number.parseFloat(ratingAvg);

  return (
    <div className="mt-3.5 mb-6 flex flex-wrap items-center gap-x-3 gap-y-1 font-mono text-meta text-content-muted">
      <span className="inline-flex items-center gap-1 text-content-muted">
        <IconHistory size={14} stroke={1.5} className="text-content-faint" />
        Turn 0
      </span>
      <span>·</span>
      {estimatedPlaytime && (
        <>
          <span className="inline-flex items-center gap-1">
            <IconClock size={14} stroke={1.5} className="text-content-faint" />
            {estimatedPlaytime} length
          </span>
          <span>·</span>
        </>
      )}
      {rating > 0 && (
        <>
          <span className="inline-flex items-center gap-1 text-accent font-medium">
            <IconStarFilled size={13} className="text-accent" />
            {rating.toFixed(1)}
          </span>
          <span>·</span>
        </>
      )}
      {playCount > 0 && <span>{playCount.toLocaleString()} plays</span>}
    </div>
  );
};
