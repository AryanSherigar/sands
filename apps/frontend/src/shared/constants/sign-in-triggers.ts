export type SignInTrigger =
  | "turn-limit"
  | "save"
  | "review"
  | "create"
  | "mobile-tab"
  | "setup";

export interface SignInTriggerCopy {
  title: string;
  benefit: string;
  isDismissible: boolean;
}

export const SIGN_IN_TRIGGER_COPY: Record<SignInTrigger, SignInTriggerCopy> = {
  "turn-limit": {
    title: "Keep your story",
    benefit: "Sign in to keep this run and carry on where you left off.",
    isDismissible: false,
  },
  save: {
    title: "Save stories to your library",
    benefit: "Sign in to bookmark stories and find them again anywhere.",
    isDismissible: true,
  },
  review: {
    title: "Sign in to review",
    benefit: "Sign in to rate this story and share what you thought.",
    isDismissible: true,
  },
  create: {
    title: "Sign in to create",
    benefit: "Sign in to write your own stories and publish them.",
    isDismissible: true,
  },
  "mobile-tab": {
    title: "Sign in to sands",
    benefit: "Sign in to sync your stories, saves and progress.",
    isDismissible: true,
  },
  setup: {
    title: "Sign in to start playing",
    benefit: "Sign in so your playthrough is saved as you go.",
    isDismissible: true,
  },
};

export const TERMS_PATH = "/terms";
export const PRIVACY_PATH = "/privacy";
