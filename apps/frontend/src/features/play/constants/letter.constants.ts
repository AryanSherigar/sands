export const LETTER_SCENE_TYPE = "letter";
export const LETTER_SEAL_MAX_CHARS = 1200;
export const SCRIBE_INSTRUCTION_MAX_CHARS = 300;

export const SCRIBE_WORKING_MESSAGE = "Your scribe is drafting.";
export const SCRIBE_UNAVAILABLE_MESSAGE = "The scribe is not available right now.";
export const SCRIBE_FAILED_MESSAGE =
  "The scribe could not write that. Your draft is unchanged.";
export const SCRIBE_INSTRUCTION_TOO_LONG_MESSAGE = `Keep the instruction under ${SCRIBE_INSTRUCTION_MAX_CHARS} characters.`;
export const SEAL_EMPTY_MESSAGE = "Write something before sealing the letter.";
export const SEAL_TOO_LONG_MESSAGE = `The letter is too long to seal. Keep it under ${LETTER_SEAL_MAX_CHARS} characters.`;
export const LETTER_DECLINED_MESSAGE = "You left the letter unanswered.";
export const SEAL_FAILED_MESSAGE = "The letter was not sent. Your draft is kept.";

export const LETTER_OUTCOME_TEXT: Readonly<Record<string, string>> = {
  letter_warmer: "Your reply warmed their regard for you.",
  letter_cooler: "Your reply cooled their regard for you.",
  letter_ack_warning: "They noted that you took their warning seriously.",
  letter_no_effect: "Your reply changed nothing between you.",
};
