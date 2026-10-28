export const PLAYER_SEES_LABEL = "Player sees";
export const WHAT_IT_MEANS_LABEL = "What it means";
export const WHAT_IT_MEANS_HELPER = "One line that tells the narrator when to change it.";
export const NEEDS_DETAILS_LABEL = "Needs details";
export const FULL_EDITOR_VALUE_NOTE = "Edit in full editor";
export const HUD_ENABLE_FAILED_MESSAGE = "Couldn't switch on the player display. Try again.";
export const VALUE_TYPE_LABEL = "Type";
export const BAR_NEEDS_BOUNDS_NOTE = "Set a lowest and highest value to show a bar or levels.";
export const CLOCK_TAKEN_NOTE = "Another value already shows the clock.";
export const LEVELS_TAKEN_NOTE = "Another value already shows levels.";
export const TRACKED_VALUES_EMPTY_COPY = "Nothing tracked yet. Add one below, or skip this step.";

export const formatInUseQuestion = (name: string, count: number): string =>
  `${name} is used in ${count} ${count === 1 ? "place" : "places"}. Delete anyway?`;

export const formatTypeChangeQuestion = (name: string, count: number): string =>
  `${name} is used in ${count} ${count === 1 ? "place" : "places"}. Changing its type may break them. Change anyway?`;

export const formatMisfitNote = (name: string, count: number): string =>
  `${name} no longer fits this comparison in ${count} ${count === 1 ? "place" : "places"}. Pick it again there.`;
