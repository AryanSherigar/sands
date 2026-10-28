import React from "react";
import { Link } from "react-router-dom";
import { PLAY_PATH_PREFIX } from "../constants/landing.constants";
import { resolveCoverImage } from "../utils/resolveCoverImage";
import { resolvePlaythroughDisplay } from "../utils/resolvePlaythroughDisplay";
import { ContinueCardThumbnail } from "./ContinueCardThumbnail";
import { ContinueCardBody } from "./ContinueCardBody";
import type { ContinueCardProps } from "./ContinueCard.types";

export const ContinueCard: React.FC<ContinueCardProps> = ({ playthrough }) => {
  const coverUrl = resolveCoverImage(
    playthrough.cover_image_url,
    playthrough.scenario_id,
  );
  const displayInfo = resolvePlaythroughDisplay(playthrough);

  return (
    <Link
      to={`${PLAY_PATH_PREFIX}/${playthrough.playthrough_id}`}
      className="group flex flex-col sm:flex-row overflow-hidden rounded-md border border-border-subtle bg-surface-raised hover:border-border-strong transition-colors duration-base focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-primary"
    >
      <ContinueCardThumbnail
        coverUrl={coverUrl}
        genre={displayInfo.genre}
      />
      <ContinueCardBody
        title={playthrough.scenario_title}
        turnCount={playthrough.turn_count}
        author={displayInfo.author}
        excerpt={displayInfo.excerpt}
        updatedAt={playthrough.updated_at}
      />
    </Link>
  );
};
