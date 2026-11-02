import type { NobleCaptive } from "../components/StrategyWarCouncil/StrategyWarCouncil.types";
import type { PrisonerView } from "../types/simulation.types";

export const prisonersToCaptives = (prisoners: PrisonerView[] | undefined): NobleCaptive[] =>
  (prisoners ?? [])
    .filter((prisoner) => prisoner.sentence_ends_turn === null)
    .map((prisoner) => ({
      nobleId: prisoner.id,
      name: prisoner.name,
      title: prisoner.title,
      factionId: prisoner.origin_faction_id,
      ransomValueGold: prisoner.ransom_value_gold,
    }));
