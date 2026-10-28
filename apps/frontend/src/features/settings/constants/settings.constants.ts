export const SETTINGS_SECTIONS = [
  { id: "account", label: "Account" },
  { id: "reading", label: "Reading" },
  { id: "content", label: "Content" },
  { id: "notifications", label: "Notifications" },
  { id: "danger", label: "Danger zone" },
] as const;

export const READER_FONT_SIZE_PIXELS: Record<string, string> = {
  small: "16px",
  medium: "18px",
  large: "22px",
};

export const LINE_HEIGHT_OPTION_LABELS: Record<string, string> = {
  comfortable: "Comfortable (1.7)",
  relaxed: "Relaxed (1.9)",
};

export const STORY_FONT_OPTION_VALUE = "";
export const STORY_FONT_OPTION_LABEL = "Use the story's font";

export const SAMPLE_PARAGRAPH_LABEL = "The Grey Ledger · Act I";
export const SAMPLE_PARAGRAPH =
  "The fog over Pier 9 was thick enough to chew. Inspector Mercer counted three carbon-copy leaves torn from the municipal vault, each stamped in indelible violet pencil. The harbor watchman swore nobody had docked since midnight, but the fresh mooring lines told a different story.";

export const AMBIENCE_VOLUME_STEP = 5;
export const PERCENT_MULTIPLIER = 100;
export const REDO_SETUP_PATH = "/welcome?redo=1";

export const DELETE_CONFIRMATION_PHRASE = "DELETE";
export const REAUTH_FAILED_MESSAGE =
  "We couldn't verify your Google account. Nothing was deleted; please try again.";
export const DELETE_FAILED_MESSAGE =
  "Something went wrong and your account was not deleted. Please try again.";
export const DELETE_REQUESTED_MESSAGE =
  "Your account is scheduled for deletion. Sign back in within 30 days to cancel.";
