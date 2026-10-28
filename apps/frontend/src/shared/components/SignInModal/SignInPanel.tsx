import React from "react";
import { AlphaConsent } from "@/features/auth/components/AlphaConsent/AlphaConsent";
import { GoogleSignInButton } from "@/features/auth/components/GoogleSignInButton/GoogleSignInButton";
import { LegalLine } from "@/features/auth/components/LegalLine/LegalLine";
import { SignInError } from "@/features/auth/components/SignInError/SignInError";
import { useAuth } from "@/features/auth/hooks/useAuth";
import type { SignInPanelProps } from "./SignInPanel.types";

export const SignInPanel: React.FC<SignInPanelProps> = ({
  copy,
  onSignedIn,
}) => {
  const { error, isGoogleLoading, loginWithGoogle } = useAuth();

  const handleSignIn = async (): Promise<void> => {
    const isSignedIn = await loginWithGoogle();
    if (isSignedIn) onSignedIn();
  };

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-content-muted">{copy.benefit}</p>
      <AlphaConsent />
      <GoogleSignInButton onClick={handleSignIn} isPending={isGoogleLoading} />
      {error && <SignInError message={error} onRetry={handleSignIn} />}
      <LegalLine />
    </div>
  );
};
