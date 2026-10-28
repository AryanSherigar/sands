export const SIGN_IN_CANCELLED_MESSAGE = "Sign-in was cancelled. Try again.";
export const SIGN_IN_FAILED_MESSAGE = "We couldn't sign you in. Try again.";

export const POPUP_CANCELLED_ERROR_CODES: readonly string[] = [
  "auth/popup-closed-by-user",
  "auth/cancelled-popup-request",
  "auth/popup-blocked",
];

export const ALPHA_ERROR_MESSAGES: Readonly<Record<string, string>> = {
  alpha_signup_closed: "Sign-up for the alpha is closed right now.",
  alpha_consent_required: "Please accept the alpha terms to continue.",
  alpha_invite_required:
    "This alpha is invite-only. Open the invite link you were sent to create an account.",
  alpha_invite_invalid:
    "This invite link isn't valid any more. Ask for a new one.",
  account_suspended:
    "This account is suspended from the alpha. Contact whoever invited you.",
};
