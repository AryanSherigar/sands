import type { ScenarioMode } from "@/shared/types/scenarioSummary.types";

export interface HeroBadgesProps {
  primaryGenre?: string;
  mode: ScenarioMode;
  contentTag?: string | null;
}
