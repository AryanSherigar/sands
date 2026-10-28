import React from "react";
import { ButtonLink } from "@/shared/components/ui/ButtonLink";
import { FALLBACK_COVER_IMAGE } from "../../constants/profileHeader.constants";
import { CampaignAbandonControl } from "./CampaignAbandonControl";
import { CampaignStatus } from "./CampaignStatus";
import type { CampaignCardProps } from "./CampaignCard.types";

export const CampaignCard: React.FC<CampaignCardProps> = ({
  campaign,
  onAbandon,
  isAbandoning = false,
}) => {
  const isActive = campaign.status === "active";
  const isCompleted = campaign.status === "completed";
  const playPath = `/play/${campaign.playthrough_id}`;
  const characterLabel = [campaign.character_name, campaign.character_archetype]
    .filter(Boolean)
    .join(" · ");

  return (
    <article className="flex flex-col overflow-hidden rounded-md border border-border-subtle bg-surface-raised transition duration-fast hover:border-border-strong motion-reduce:transition-none sm:flex-row">
      <img
        src={campaign.cover_image_url || FALLBACK_COVER_IMAGE}
        alt={campaign.scenario_title}
        className="h-36 w-full shrink-0 object-cover sm:h-auto sm:w-48"
      />
      <div className="flex flex-1 flex-col gap-3 p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="font-display text-lg font-semibold text-content">
            {campaign.scenario_title}
          </h3>
          <CampaignStatus campaign={campaign} />
        </div>
        <p className="flex flex-wrap items-center gap-2 font-mono text-xs text-content-muted">
          <span>Turn {campaign.turn_count}</span>
          {characterLabel && <span>· {characterLabel}</span>}
          <span className="capitalize">· {campaign.scenario_mode}</span>
        </p>
        {isCompleted && campaign.ended_outcome_title && (
          <p className="line-clamp-1 text-sm text-content-muted">
            {campaign.ended_outcome_title}
          </p>
        )}
        <div className="mt-auto flex flex-wrap items-center justify-between gap-3 border-t border-border-subtle pt-3">
          <div className="flex items-center gap-2">
            <ButtonLink to={playPath} variant="secondary" size="sm">
              {isActive ? "Continue" : "View recap"}
            </ButtonLink>
            {isCompleted && (
              <ButtonLink
                to={`/scenario/${campaign.scenario_id}`}
                variant="ghost"
                size="sm"
              >
                Review scenario
              </ButtonLink>
            )}
          </div>
          {isActive && (
            <CampaignAbandonControl
              onConfirm={() => onAbandon(campaign.playthrough_id)}
              isAbandoning={isAbandoning}
            />
          )}
        </div>
      </div>
    </article>
  );
};
