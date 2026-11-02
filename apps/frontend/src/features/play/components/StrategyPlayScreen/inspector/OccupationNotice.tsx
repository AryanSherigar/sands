import React from "react";
import { resolveOwnerLabel } from "../../../lib/factionLabels";
import type { CampaignWorldView, RegionView } from "../../../types/simulation.types";

interface OccupationNoticeProps {
  regionView?: RegionView;
  world?: CampaignWorldView;
}

function describeNotice(
  regionView: RegionView,
  world: CampaignWorldView | undefined,
): string | null {
  if (regionView.occupation) {
    const occupier = resolveOwnerLabel(world, regionView.occupation.occupier_id);
    return `Occupied by ${occupier} (held ${regionView.occupation.hold_turns} turns)`;
  }
  if (regionView.siege) {
    const besieger = resolveOwnerLabel(world, regionView.siege.besieger_id);
    return `Besieged by ${besieger}: ${regionView.siege.progress}%`;
  }
  return null;
}

export const OccupationNotice: React.FC<OccupationNoticeProps> = ({ regionView, world }) => {
  const message = regionView ? describeNotice(regionView, world) : null;
  if (!message) return null;
  return (
    <p className="mx-3 px-2 py-1 rounded bg-[#A8483E]/15 text-xs font-bold text-[#A8483E]">
      {message}
    </p>
  );
};
