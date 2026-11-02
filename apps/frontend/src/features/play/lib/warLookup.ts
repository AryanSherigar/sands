import type { CampaignWorldView } from "../types/simulation.types";

type WarLookupWorld = Pick<
  CampaignWorldView,
  "wars" | "pending_calls" | "open_mediations" | "subsidies"
>;

export function findActiveWarId(
  world: WarLookupWorld | undefined,
  myFactionId: string | undefined,
  ownerId: string,
): string | undefined {
  if (!world) return undefined;
  if (world.wars) {
    const war = world.wars.find(
      (w) =>
        (w.attacker_id === ownerId && w.defender_id === myFactionId) ||
        (w.attacker_id === myFactionId && w.defender_id === ownerId) ||
        (myFactionId &&
          w.participant_ids?.includes(myFactionId) &&
          (w.attacker_id === ownerId || w.defender_id === ownerId || w.participant_ids?.includes(ownerId))),
    );
    if (war) return war.id;
  }
  const call = world.pending_calls?.find((c) => c.caller_id === ownerId);
  if (call) return call.war_id;
  const mediation = world.open_mediations?.find((m) => m.mediator_id === ownerId);
  if (mediation) return mediation.war_id;
  const subsidy = world.subsidies?.find((s) => s.payer_id === ownerId || s.receiver_id === ownerId);
  if (subsidy) return subsidy.war_id;
  return undefined;
}
