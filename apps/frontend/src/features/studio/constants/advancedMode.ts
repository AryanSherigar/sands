export const ADVANCED_MODE_LABEL = "Advanced mode";
export const ADVANCED_NARROW_NOTICE = "Advanced mode works on a larger screen.";
export const ADVANCED_SWITCH_FAILED_MESSAGE = "Couldn't switch Advanced mode. Try again.";
export const ADVANCED_TURN_OFF_TITLE = "Turn off Advanced mode?";
export const ADVANCED_TURN_OFF_COPY =
  'Your endings, values and rules are kept but switched off. Links with an "only when" condition stop applying until you turn Advanced mode back on. Turn it back on anytime to use everything again.';
export const ADVANCED_TURN_OFF_CONFIRM_LABEL = "Turn off Advanced mode";
export const ADVANCED_RAIL_LABEL = "Advanced";
export const ADVANCED_MODE_ON = "master";
export const ADVANCED_MODE_OFF = "newbie";
export const buildMissingPublishWarning = (missingItems: readonly string[]): string =>
  `Without Advanced mode, publishing needs: ${missingItems.join(", ")}. Add ${missingItems.length === 1 ? "it" : "them"} before you publish changes.`;
