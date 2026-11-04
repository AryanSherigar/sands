import React, { useState } from "react";
import type { EmailSignInFormProps } from "./EmailSignInForm.types";

const INPUT_CLASSES =
  "w-full rounded-md border border-border-subtle bg-surface-raised px-3 py-2 font-sans text-sm text-content placeholder:text-content-faint focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent";

export const EmailSignInForm: React.FC<EmailSignInFormProps> = ({
  onSubmit,
  isPending,
  errorMessage = null,
}) => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const isIncomplete = email.trim() === "" || password === "";

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>): void => {
    event.preventDefault();
    if (isPending || isIncomplete) return;
    void onSubmit(email.trim(), password);
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3">
      <label className="flex flex-col gap-1 font-sans text-xs text-content-muted">
        Email
        <input
          type="email"
          autoComplete="username"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          className={INPUT_CLASSES}
        />
      </label>
      <label className="flex flex-col gap-1 font-sans text-xs text-content-muted">
        Password
        <input
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          className={INPUT_CLASSES}
        />
      </label>
      {errorMessage && (
        <p role="alert" className="font-sans text-xs text-danger">
          {errorMessage}
        </p>
      )}
      <button
        type="submit"
        disabled={isPending}
        className="rounded-lg border border-border-subtle bg-surface-raised px-4 py-2 font-sans text-sm font-medium text-content transition hover:bg-surface-overlay focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isPending ? "Signing in…" : "Sign in"}
      </button>
    </form>
  );
};
