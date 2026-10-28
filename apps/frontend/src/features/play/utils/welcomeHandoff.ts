const HANDOFF_PREFIX = "welcome-handoff:";

export function getWelcomeHandoff(scenarioId: string): string | null {
  return sessionStorage.getItem(HANDOFF_PREFIX + scenarioId);
}

export function saveWelcomeHandoff(scenarioId: string, playthroughId: string): void {
  sessionStorage.setItem(HANDOFF_PREFIX + scenarioId, playthroughId);
}

export function clearWelcomeHandoff(scenarioId: string): void {
  sessionStorage.removeItem(HANDOFF_PREFIX + scenarioId);
}

export function hasWelcomeTape(worldData?: Record<string, unknown>): boolean {
  const presentation = worldData?.presentation;
  return typeof presentation === "object" && presentation !== null
    && "welcome_tape_id" in presentation && presentation.welcome_tape_id === "tallis-v1";
}
