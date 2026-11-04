import type { PlayerRulerPayload } from "@/shared/api/playthroughs.api";
import type { StrategyRulerState } from "./StrategyRulerSetup.types";

export function buildPlayerRulerPayload(ruler: StrategyRulerState): PlayerRulerPayload {
  return {
    name: ruler.name,
    epithet: ruler.epithet || null,
    portrait_url: ruler.portraitUrl || null,
    trait_ids: ruler.traitIds,
    ambition_ids: ruler.ambitionIds,
    backstory: ruler.backstory,
    chronicler_id: ruler.chroniclerId,
  };
}
