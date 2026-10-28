import React from "react";
import { SIGN_IN_FAILED_MESSAGE } from "../../constants/auth-messages";
import type { SignInErrorProps } from "./SignInError.types";

export const SignInError: React.FC<SignInErrorProps> = ({
  message,
  onRetry,
}) => {
  const shouldOfferRetry = message === SIGN_IN_FAILED_MESSAGE;

  return (
    <div
      role="alert"
      className="flex items-center gap-2 rounded-md border border-danger/40 bg-danger/10 px-3 py-2 font-sans text-xs text-danger"
    >
      <span>{message}</span>
      {shouldOfferRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="font-medium underline focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent"
        >
          Retry
        </button>
      )}
    </div>
  );
};
