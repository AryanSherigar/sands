import type { StrategyDispatchView } from "../../../types/simulation.types";

const TOPIC_SUBJECTS: Record<string, string> = {
  will: "the rival's resolve",
  strain: "the strain of war upon the rival",
  rage: "the anger of the rival's court",
  threat: "the threat the rival poses",
  health: "the health of the rival's ruler",
  coalition: "the realms united against the rival",
};

export const formatFactionName = (factionId: string): string =>
  factionId
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");

export const formatTraits = (dispatch: StrategyDispatchView): string =>
  dispatch.agent.traits.join(", ");

export const buildFallbackNote = (dispatch: StrategyDispatchView): string => {
  const [topic, ...bandParts] = dispatch.fallback_line_key.split(".");
  const subject = TOPIC_SUBJECTS[topic] ?? "the rival";
  const band = bandParts.join(".").replace(/_/g, " ");
  return `${dispatch.agent.name} sends only a short note: ${subject} is reported as ${band}.`;
};
