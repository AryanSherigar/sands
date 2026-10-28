import React from "react";
import { useAuthStore } from "../stores/auth.store";
import { useAuth } from "../hooks/useAuth";
import { ALPHA_ERROR_MESSAGES } from "../constants/auth-messages";
import { useLoginRedirect } from "../hooks/useLoginRedirect";
import { LoginHero } from "../components/LoginHero/LoginHero";
import { GoogleSignInButton } from "../components/GoogleSignInButton/GoogleSignInButton";
import { AlphaConsent } from "../components/AlphaConsent/AlphaConsent";
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
  const isSuspended = useAuthStore((state) => state.isSuspended);
  const { error, isGoogleLoading, loginWithGoogle, loginAsDevUser } =
    useAuth();
  useLoginRedirect();
  const signInError =
    error ?? (isSuspended ? ALPHA_ERROR_MESSAGES.account_suspended : null);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-surface">
        <Loader size="lg" label="Loading" />
      </div>
    );
  }

  return (
    <main className="flex min-h-screen flex-col bg-surface text-content lg:flex-row">
      <div className="h-[30dvh] w-full bg-surface-sunken lg:order-last lg:h-auto lg:min-h-screen lg:w-[55%]">
        <LoginHero />
      </div>

      <div className="flex flex-1 items-center px-8 py-12 sm:px-14 lg:w-[45%] lg:flex-none lg:px-16">
        <div className="w-full max-w-md">
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
            <AlphaConsent />
            <GoogleSignInButton
              onClick={loginWithGoogle}
              isPending={isGoogleLoading}
            />
            {signInError && (
              <SignInError message={signInError} onRetry={loginWithGoogle} />
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
