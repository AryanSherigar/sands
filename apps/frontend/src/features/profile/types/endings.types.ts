export interface EndingSlot {
  is_found: boolean;
  title: string | null;
  outcome_tag: "win" | "lose" | null;
}

export interface ScenarioEndings {
  scenario_id: string;
  scenario_title: string;
  found_count: number;
  total_count: number;
  slots: EndingSlot[];
}

export interface ProfileEndings {
  scenarios: ScenarioEndings[];
}
