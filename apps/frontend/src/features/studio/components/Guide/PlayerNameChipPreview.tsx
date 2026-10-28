import React from "react";
import { PLAYER_NAME_CHIP_LABEL } from "../../constants/opening";
import { hasPlayerNameToken, splitOnPlayerName } from "../../lib/openingToken";
import type { PlayerNameChipPreviewProps } from "./Guide.types";

export const PlayerNameChipPreview: React.FC<PlayerNameChipPreviewProps> = ({ document }) => {
  if (!hasPlayerNameToken(document)) return null;
  const blocksWithToken = document.blocks.filter((block) => splitOnPlayerName(block.text).some((segment) => segment.isPlayerName));

  return (
    <div aria-label="How the opening reads" className="space-y-1 rounded-md bg-surface-raised px-3 py-2 text-meta text-content-muted">
      {blocksWithToken.map((block, blockIndex) => (
        <p key={blockIndex} className="whitespace-pre-line">
          {splitOnPlayerName(block.text).map((segment, segmentIndex) =>
            segment.isPlayerName ? (
              <span
                key={segmentIndex}
                data-token-chip
                className="mx-0.5 rounded-sm border border-primary px-1.5 py-0.5 text-micro font-medium text-content"
              >
                {PLAYER_NAME_CHIP_LABEL}
              </span>
            ) : (
              <span key={segmentIndex}>{segment.text}</span>
            ),
          )}
        </p>
      ))}
    </div>
  );
};
