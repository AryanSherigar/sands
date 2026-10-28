import type { ScenarioUpdate } from "./scenario.types";

export type ScenarioFieldsPatch = Omit<
  ScenarioUpdate,
  "world_data" | "expected_content_edited_at" | "status"
> & {
  worldData?: Record<string, unknown>;
};
