export const SIGN_IN_CANCELLED_MESSAGE = "Sign-in was cancelled. Try again.";
export const SIGN_IN_FAILED_MESSAGE = "We couldn't sign you in. Try again.";

export const POPUP_CANCELLED_ERROR_CODES: readonly string[] = [
  "auth/popup-closed-by-user",
  "auth/cancelled-popup-request",
  "auth/popup-blocked",
];

export const EMAIL_SIGN_IN_INVALID_MESSAGE =
  "That email and password don't match.";

export const EMAIL_INVALID_CREDENTIAL_ERROR_CODES: readonly string[] = [
  "auth/invalid-credential",
  "auth/wrong-password",
  "auth/user-not-found",
  "auth/invalid-email",
];
