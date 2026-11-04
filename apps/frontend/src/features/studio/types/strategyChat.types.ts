import type { AssistantStrategyContextPayload } from "./assistant.types";
import type { StrategyActionApplier } from "../hooks/useStrategyActionApplier";

export interface StrategyChatBinding {
  context: AssistantStrategyContextPayload;
  applier: StrategyActionApplier;
}
