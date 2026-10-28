export const CARD_VALUES_HEADING = "Values";
export const CARD_VALUES_HELPER =
  "Numbers and yes / no facts about this card, like Health or Trust. Endings and rules can use them.";
export const CARD_VALUES_EMPTY_COPY = "No values yet.";
export const CARD_VALUE_NAME_LABEL = "New value name";
export const CARD_VALUE_ADD_LABEL = "Add value";
export const CARD_VALUE_NARRATOR_LABEL = "The narrator always sees this";
export const CARD_VALUE_SAVE_FAILED_MESSAGE = "Couldn't save the values. Try again.";
export const CARD_VALUE_KIND_OPTIONS = [
  { value: "number", label: "Number" },
  { value: "boolean", label: "Yes / no" },
] as const;
export const LINK_WHEN_LABEL = "Only when…";
export const LINK_TARGET_CARD = "card";
export const LINK_TARGET_TEXT = "text";
export const LINK_TARGET_OPTIONS = [
  { value: LINK_TARGET_CARD, label: "A card" },
  { value: LINK_TARGET_TEXT, label: "Plain text" },
] as const;
export const LINK_TEXT_LABEL = "Plain text";
export const LINK_TEXT_PLACEHOLDER = "70 years old";
