const REJECT_REASON_TEXT: Record<string, string> = {
  unknown_army: "That army could not be found.",
  not_your_army: "That army is not under your command.",
  faction_destroyed: "That house no longer exists.",
  unknown_faction: "That house could not be found.",
  empty_army: "That army has no troops left.",
  commander_unavailable: "The army's commander is unavailable.",
  in_battle: "That army is locked in battle.",
  unknown_region: "That region could not be found.",
  already_there: "The army is already in that region.",
  no_route: "No route reaches that region.",
  avoid_blocks_goal: "Your avoid orders block the only route there.",
  duplicate_order: "That order has already been given this turn.",
  target_not_hostile: "You can only attack a region held by a house you are at war with.",
  not_your_region: "That region is not yours.",
  region_occupied: "That region is occupied by an enemy.",
  empty_levy: "A levy needs at least one soldier.",
  insufficient_manpower: "Not enough manpower for that levy.",
  insufficient_funds: "Not enough gold for that order.",
  loans_disabled: "Loans are not available in this realm.",
  invalid_amount: "That amount is not valid.",
  no_credit: "No lender will extend you credit.",
  army_busy: "That army is already carrying out an order.",
  different_location: "The armies must be in the same region.",
  invalid_merge: "Those armies cannot be merged.",
  invalid_split: "That army cannot be split that way.",
};

const REFUSED_FALLBACK_MESSAGE = "That order cannot be issued right now";

const RAW_CODE_PATTERN = /^[a-z]+(_[a-z]+)*$/;

export function describeRejectReason(reason: string | null | undefined): string {
  if (!reason) return REFUSED_FALLBACK_MESSAGE;
  if (reason in REJECT_REASON_TEXT) return REJECT_REASON_TEXT[reason];
  return RAW_CODE_PATTERN.test(reason) ? REFUSED_FALLBACK_MESSAGE : reason;
}
