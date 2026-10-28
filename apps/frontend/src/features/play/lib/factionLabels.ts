import type { CampaignWorldView } from "../types/simulation.types";

const OWN_REALM_LABEL = "Your realm";
const UNCLAIMED_LABEL = "Unclaimed";

export function resolveOwnerLabel(
  world: Pick<CampaignWorldView, "my_faction" | "rivals"> | undefined,
  ownerId: string | null | undefined,
): string {
  if (!ownerId) return UNCLAIMED_LABEL;
  if (ownerId === world?.my_faction.id) return OWN_REALM_LABEL;
  return world?.rivals.find((rival) => rival.faction_id === ownerId)?.name ?? ownerId;
}
