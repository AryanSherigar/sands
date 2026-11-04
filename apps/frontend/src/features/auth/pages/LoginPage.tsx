import React, { useState } from "react";
import { useAuthStore } from "../stores/auth.store";
import { useAuth } from "../hooks/useAuth";
import { useLoginRedirect } from "../hooks/useLoginRedirect";
import { LoginHero } from "../components/LoginHero/LoginHero";
import { GoogleSignInButton } from "../components/GoogleSignInButton/GoogleSignInButton";
import { EmailSignInForm } from "../components/EmailSignInForm/EmailSignInForm";
import { LegalLine } from "../components/LegalLine/LegalLine";
import { SignInError } from "../components/SignInError/SignInError";
import { LayoutTextFlip } from "@/shared/components/ui/aceternity/layout-text-flip";
import { Loader } from "@/shared/components/feedback/Loader";

const FLIP_WORDS = [
  "a new world",
  "a living story",
  "your legend",
  "the unknown",
];
const ACCESSIBLE_HEADLINE = `Step into ${FLIP_WORDS[0]}`;
const FLIP_CLASSES =
  "bg-surface-raised text-content ring-border-subtle shadow-none";

export const LoginPage: React.FC = () => {
  const isLoading = useAuthStore((state) => state.isLoading);
  const {
    error,
    emailError,
    isGoogleLoading,
    isEmailLoading,
    loginWithGoogle,
    loginWithEmail,
    loginAsDevUser,
  } = useAuth();
  const [isEmailFormOpen, setIsEmailFormOpen] = useState(false);
  useLoginRedirect();

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-surface">
        <Loader size="lg" label="Loading" />
      </div>
    );
  }

  return (
    <main className="flex min-h-screen flex-col bg-surface text-content lg:flex-row">
      <div className="h-[30dvh] w-full bg-surface-sunken lg:order-last lg:h-auto lg:min-h-screen lg:w-2/3">
        <LoginHero />
      </div>

      <div className="flex flex-1 items-center px-6 py-12 sm:px-10 lg:w-1/3 lg:flex-none lg:px-10 xl:px-14">
        <div className="w-full max-w-sm">
          <span className="block font-mono text-5xl font-semibold lowercase tracking-[0.12em] text-content sm:text-6xl">
            sands
          </span>

          <h1 className="sr-only">{ACCESSIBLE_HEADLINE}</h1>
          <div
            aria-hidden="true"
            className="mt-8 flex flex-row flex-nowrap items-center gap-x-2 whitespace-nowrap"
          >
            <LayoutTextFlip
              text="Step into"
              words={FLIP_WORDS}
              size="sm"
              className={FLIP_CLASSES}
              textClassName="text-content"
            />
          </div>

          <p className="mt-4 font-sans text-sm text-content-muted">
            Sign in to keep your stories, saves and progress.
          </p>

          <div className="mt-8 flex flex-col gap-4">
            <GoogleSignInButton
              onClick={loginWithGoogle}
              isPending={isGoogleLoading}
            />
            {error && (
              <SignInError message={error} onRetry={loginWithGoogle} />
            )}
            <button
              type="button"
              aria-expanded={isEmailFormOpen}
              onClick={() => setIsEmailFormOpen((isOpen) => !isOpen)}
              className="self-start font-sans text-xs text-content-muted underline decoration-dotted underline-offset-4 transition hover:text-content focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent"
            >
              Sign in with email
            </button>
            {isEmailFormOpen && (
              <EmailSignInForm
                onSubmit={loginWithEmail}
                isPending={isEmailLoading}
                errorMessage={emailError}
              />
            )}
          </div>

          <div className="mt-8">
            <LegalLine />
          </div>

          {import.meta.env.DEV && (
            <button
              onClick={loginAsDevUser}
              className="mt-6 font-mono text-xs text-content-faint underline decoration-dotted underline-offset-4 transition hover:text-content-muted focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent"
            >
              Dev login bypass
            </button>
          )}
        </div>
      </div>
    </main>
  );
};
